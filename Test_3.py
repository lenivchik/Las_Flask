import lascheck
from typing import Dict, List, Any, Tuple
import re
import traceback
from enum import Enum

class ErrorSeverity(Enum):
    """Error severity levels"""
    CRITICAL = "critical"  # File cannot be processed
    ERROR = "error"        # Specification violation
    WARNING = "warning"    # Non-critical issue
    INFO = "info"         # Informational message

class ErrorCategory(Enum):
    """Error categories for better organization"""
    STRUCTURE = "structure"
    HEADER = "header"
    DATA = "data"
    FORMAT = "format"
    ENCODING = "encoding"

def validate_las_file_enhanced(file_path: str, **kwargs) -> Dict[str, Any]:
    """
    Enhanced LAS file validation with categorized errors and detailed analysis.
    
    Args:
        file_path (str): Path to the LAS file to validate
        **kwargs: Additional arguments to pass to lascheck.read()
    
    Returns:
        Dict containing:
        - summary: General summary message
        - errors: Categorized list of errors with severity
        - warnings: List of warnings
        - info: Additional information about the file
        - statistics: File statistics
        - valid: Boolean indicating if file is valid
        - score: Validation score (0-100)
    """
    
    errors = []
    warnings = []
    info = []
    statistics = {}
    
    try:
        # Step 1: Basic file validation
        file_stats = _validate_file_basics(file_path)
        statistics.update(file_stats)
        
        # Step 2: Try to read the file with different strategies
        las_file, read_errors = _read_las_with_fallback(file_path, **kwargs)
        errors.extend(read_errors)
        
        if las_file:
            # Step 3: Structural validation
            struct_errors, struct_warnings = _validate_structure(las_file)
            errors.extend(struct_errors)
            warnings.extend(struct_warnings)
            
            # Step 4: Header validation
            header_errors, header_warnings, header_info = _validate_headers(las_file)
            errors.extend(header_errors)
            warnings.extend(header_warnings)
            info.extend(header_info)
            
            # Step 5: Data validation
            data_errors, data_warnings, data_stats = _validate_data(las_file)
            errors.extend(data_errors)
            warnings.extend(data_warnings)
            statistics.update(data_stats)
            
            # Step 6: Get library non-conformities
            lib_errors = _get_library_errors(las_file)
            errors.extend(lib_errors)
            
    except Exception as e:
        errors.append({
            "severity": ErrorSeverity.CRITICAL,
            "category": ErrorCategory.STRUCTURE,
            "message": f"Критическая ошибка при обработке файла: {str(e)}",
            "details": traceback.format_exc()
        })
    
    # Calculate validation score
    score = _calculate_validation_score(errors, warnings)
    
    # Prepare final results
    results = {
        "summary": _generate_summary(errors, warnings, score),
        "errors": [_format_error(e) for e in errors],
        "warnings": [_format_error(w) for w in warnings],
        "info": info,
        "statistics": statistics,
        "valid": len([e for e in errors if e["severity"] == ErrorSeverity.ERROR]) == 0,
        "score": score,
        "error_count": {
            "critical": len([e for e in errors if e["severity"] == ErrorSeverity.CRITICAL]),
            "error": len([e for e in errors if e["severity"] == ErrorSeverity.ERROR]),
            "warning": len(warnings)
        }
    }
    
    return results

def _validate_file_basics(file_path: str) -> Dict[str, Any]:
    """Validate basic file properties"""
    import os
    
    stats = {}
    
    try:
        file_size = os.path.getsize(file_path)
        stats["file_size_bytes"] = file_size
        stats["file_size_mb"] = round(file_size / (1024 * 1024), 2)
        
        # Check if file is too large
        if file_size > 100 * 1024 * 1024:  # 100MB
            stats["size_warning"] = "Файл очень большой, обработка может занять время"
            
    except FileNotFoundError:
        raise FileNotFoundError(f"Файл не найден: {file_path}")
    except Exception as e:
        stats["file_error"] = str(e)
        
    return stats

def _read_las_with_fallback(file_path: str, **kwargs) -> Tuple[Any, List[Dict]]:
    """Try to read LAS file with different strategies"""
    errors = []
    las_file = None
    
    # Strategy 1: Try with header errors ignored
    try:
        las_file = lascheck.read(file_path, ignore_header_errors=True, **kwargs)
    except lascheck.exceptions.LASHeaderError as e:
        errors.append({
            "severity": ErrorSeverity.ERROR,
            "category": ErrorCategory.HEADER,
            "message": f"Ошибка заголовка: {str(e)}"
        })
        # Try without header validation
        try:
            las_file = lascheck.read(file_path, ignore_header_errors=True, ignore_data=True, **kwargs)
        except Exception as e2:
            errors.append({
                "severity": ErrorSeverity.CRITICAL,
                "category": ErrorCategory.FORMAT,
                "message": f"Невозможно прочитать файл даже с игнорированием ошибок: {str(e2)}"
            })
    except Exception as e:
        errors.append({
            "severity": ErrorSeverity.CRITICAL,
            "category": ErrorCategory.FORMAT,
            "message": f"Ошибка чтения файла: {str(e)}"
        })
        
    return las_file, errors

def _validate_structure(las_file) -> Tuple[List[Dict], List[Dict]]:
    """Validate LAS file structure"""
    errors = []
    warnings = []
    
    # Check for mandatory sections
    mandatory_sections = {
        "Version": "~V",
        "Well": "~W", 
        "Curves": "~C",
        "Ascii": "~A"
    }
    
    for section_name, section_marker in mandatory_sections.items():
        if section_name not in las_file.sections:
            errors.append({
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.STRUCTURE,
                "message": f"Отсутствует обязательная секция {section_marker}"
            })
    
    # Check section order
    if hasattr(las_file, 'v_section_first') and not las_file.v_section_first:
        errors.append({
            "severity": ErrorSeverity.ERROR,
            "category": ErrorCategory.STRUCTURE,
            "message": "Секция ~V должна быть первой"
        })
    
    # Check for duplicate sections
    if hasattr(las_file, 'duplicate_v_section') and las_file.duplicate_v_section:
        errors.append({
            "severity": ErrorSeverity.ERROR,
            "category": ErrorCategory.STRUCTURE,
            "message": "Обнаружена дублирующаяся секция ~V"
        })
        
    # Check for sections after ~A
    if hasattr(las_file, 'sections_after_a_section') and las_file.sections_after_a_section:
        errors.append({
            "severity": ErrorSeverity.ERROR,
            "category": ErrorCategory.STRUCTURE,
            "message": "Обнаружены секции после секции ~A (она должна быть последней)"
        })
        
    # Check for blank lines in sections
    if hasattr(las_file, 'sections_with_blank_line'):
        for section in las_file.sections_with_blank_line:
            warnings.append({
                "severity": ErrorSeverity.WARNING,
                "category": ErrorCategory.FORMAT,
                "message": f"Пустые строки в секции {section}"
            })
            
    return errors, warnings

def _validate_headers(las_file) -> Tuple[List[Dict], List[Dict], List[str]]:
    """Validate header sections"""
    errors = []
    warnings = []
    info = []
    
    # Validate Version section
    if "Version" in las_file.sections:
        version_section = las_file.version
        
        # Check mandatory fields
        if "VERS" not in version_section:
            errors.append({
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.HEADER,
                "message": "Отсутствует обязательное поле VERS в секции ~V"
            })
        else:
            vers_value = version_section["VERS"].value
            info.append(f"LAS версия: {vers_value}")
            
            if vers_value not in [1.2, 2.0]:
                warnings.append({
                    "severity": ErrorSeverity.WARNING,
                    "category": ErrorCategory.HEADER,
                    "message": f"Нестандартная версия LAS: {vers_value}"
                })
                
        if "WRAP" not in version_section:
            errors.append({
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.HEADER,
                "message": "Отсутствует обязательное поле WRAP в секции ~V"
            })
    
    # Validate Well section
    if "Well" in las_file.sections:
        well_section = las_file.well
        mandatory_well_fields = [
            "STRT", "STOP", "STEP", "NULL", "COMP", 
            "WELL", "FLD", "LOC", "SRVC", "DATE"
        ]
        
        for field in mandatory_well_fields:
            if field not in well_section:
                errors.append({
                    "severity": ErrorSeverity.ERROR,
                    "category": ErrorCategory.HEADER,
                    "message": f"Отсутствует обязательное поле {field} в секции ~W"
                })
                
        # Check for UWI or API
        if "UWI" not in well_section and "API" not in well_section:
            errors.append({
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.HEADER,
                "message": "Должно быть указано хотя бы одно из полей: UWI или API"
            })
            
        # Check for location fields
        location_fields = ["PROV", "CNTY", "CTRY", "STAT"]
        if not any(field in well_section for field in location_fields):
            warnings.append({
                "severity": ErrorSeverity.WARNING,
                "category": ErrorCategory.HEADER,
                "message": "Рекомендуется указать хотя бы одно поле местоположения: PROV, CNTY, CTRY или STAT"
            })
            
        # Extract well info
        if "WELL" in well_section:
            info.append(f"Скважина: {well_section['WELL'].value}")
        if "FLD" in well_section:
            info.append(f"Месторождение: {well_section['FLD'].value}")
            
    return errors, warnings, info

def _validate_data(las_file) -> Tuple[List[Dict], List[Dict], Dict]:
    """Validate data section and curves"""
    errors = []
    warnings = []
    stats = {}
    
    if "Curves" not in las_file.sections:
        return errors, warnings, stats
        
    curves = las_file.curves
    
    if len(curves) == 0:
        errors.append({
            "severity": ErrorSeverity.ERROR,
            "category": ErrorCategory.DATA,
            "message": "Не найдено ни одной кривой в файле"
        })
        return errors, warnings, stats
        
    # Validate index curve
    index_curve = curves[0]
    valid_index_mnemonics = ["DEPT", "DEPTH", "TIME", "INDEX"]
    
    if index_curve.mnemonic.upper() not in valid_index_mnemonics:
        errors.append({
            "severity": ErrorSeverity.ERROR,
            "category": ErrorCategory.DATA,
            "message": f"Некорректная индексная кривая: {index_curve.mnemonic}. Допустимые: {', '.join(valid_index_mnemonics)}"
        })
        
    # Check depth units if index is depth
    if index_curve.mnemonic.upper() in ["DEPT", "DEPTH"]:
        valid_units = ["M", "F", "FT"]
        if index_curve.unit.upper() not in valid_units:
            errors.append({
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.DATA,
                "message": f"Некорректные единицы измерения глубины: {index_curve.unit}. Допустимые: {', '.join(valid_units)}"
            })
            
    # Collect statistics
    stats["curve_count"] = len(curves)
    stats["curve_names"] = [c.mnemonic for c in curves]
    
    # Check for duplicate curve names
    curve_names = [c.mnemonic for c in curves]
    duplicates = [name for name in curve_names if curve_names.count(name) > 1]
    if duplicates:
        unique_duplicates = list(set(duplicates))
        warnings.append({
            "severity": ErrorSeverity.WARNING,
            "category": ErrorCategory.DATA,
            "message": f"Обнаружены дублирующиеся имена кривых: {', '.join(unique_duplicates)}"
        })
        
    return errors, warnings, stats

def _get_library_errors(las_file) -> List[Dict]:
    """Get errors from lascheck library"""
    errors = []
    
    try:
        non_conformities = las_file.get_non_conformities()
        for error_msg in non_conformities:
            # Skip duplicates that we've already handled
            if any(keyword in error_msg.lower() for keyword in ['duplicate', 'section', 'first']):
                continue
                
            errors.append({
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.FORMAT,
                "message": error_msg
            })
    except Exception as e:
        pass  # Ignore if method not available
        
    return errors

def _calculate_validation_score(errors: List[Dict], warnings: List[Dict]) -> int:
    """Calculate a validation score from 0-100"""
    score = 100
    
    # Deduct points for errors
    for error in errors:
        if error["severity"] == ErrorSeverity.CRITICAL:
            score -= 30
        elif error["severity"] == ErrorSeverity.ERROR:
            score -= 10
            
    # Deduct points for warnings
    score -= len(warnings) * 2
    
    return max(0, score)

def _generate_summary(errors: List[Dict], warnings: List[Dict], score: int) -> str:
    """Generate a summary message"""
    critical_count = len([e for e in errors if e["severity"] == ErrorSeverity.CRITICAL])
    error_count = len([e for e in errors if e["severity"] == ErrorSeverity.ERROR])
    warning_count = len(warnings)
    
    if critical_count > 0:
        return f"Файл содержит критические ошибки ({critical_count}) и не может быть обработан"
    elif error_count > 0:
        return f"Файл проверен. Обнаружено ошибок: {error_count}, предупреждений: {warning_count}. Оценка: {score}/100"
    elif warning_count > 0:
        return f"Файл проверен. Предупреждений: {warning_count}. Оценка: {score}/100"
    else:
        return f"Файл полностью соответствует стандарту LAS. Оценка: {score}/100"

def _format_error(error: Dict) -> str:
    """Format error for display"""
    if isinstance(error, str):
        return error
    return error.get("message", str(error))