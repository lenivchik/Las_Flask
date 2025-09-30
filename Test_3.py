import lascheck
from typing import Dict, List, Any, Tuple
import re
import traceback
from enum import Enum
import time

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
    print("LOL")
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
            # Step 3: Get library errors and warnings
            lib_errors, lib_warnings = _get_library_issues(las_file)
            errors.extend(lib_errors)
            warnings.extend(lib_warnings)
            
            # Step 4: Collect additional statistics and info
            statistics.update(_collect_statistics(las_file))
            info.extend(_collect_info(las_file))
            
    except Exception as e:
        errors.append({
            "severity": ErrorSeverity.CRITICAL,
            "category": ErrorCategory.STRUCTURE,
            "message": f"Критическая ошибка при обработке файла: {str(e)}",
            "details": traceback.format_exc()
        })
    

    # Prepare final results
    results = {
        "summary": _generate_summary(errors, warnings),
        "errors": [_format_error(e) for e in errors],
        "warnings": [_format_error(w) for w in warnings],
        "info": info,
        "statistics": statistics,
        "valid": len([e for e in errors if e["severity"] in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]]) == 0,
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
    
    # Strategy 1: Try with default settings
    try:
        las_file = lascheck.read(file_path, **kwargs)
        return las_file, errors
    except lascheck.exceptions.LASHeaderError as e:
        errors.append({
            "severity": ErrorSeverity.ERROR,
            "category": ErrorCategory.HEADER,
            "message": f"Ошибка заголовка: {str(e)}"
        })
    except Exception as e:
        pass  # Try next strategy
    
    # Strategy 2: Try with header errors ignored
    try:
        las_file = lascheck.read(file_path, ignore_header_errors=True, **kwargs)
        return las_file, errors
    except Exception as e:
        pass  # Try next strategy
    
    # Strategy 3: Try without data (headers only)
    try:
        las_file = lascheck.read(file_path, ignore_header_errors=True, ignore_data=True, **kwargs)
        if las_file:
            errors.append({
                "severity": ErrorSeverity.WARNING,
                "category": ErrorCategory.DATA,
                "message": "Данные не могут быть прочитаны, проверены только заголовки"
            })
        return las_file, errors
    except Exception as e:
        errors.append({
            "severity": ErrorSeverity.CRITICAL,
            "category": ErrorCategory.FORMAT,
            "message": f"Невозможно прочитать файл: {str(e)}"
        })
        return None, errors

def _get_library_issues(las_file) -> Tuple[List[Dict], List[Dict]]:
    """Get errors and warnings from lascheck library"""
    errors = []
    warnings = []
    
    try:
        # Try to use the new API with warnings support
        if hasattr(las_file, 'get_all_issues'):
            issues = las_file.get_all_issues()
            
            # Process errors
            for error_msg in issues.get('errors', []):
                # Skip duplicate messages we might have already handled
                if not _is_duplicate_message(error_msg, errors):
                    errors.append({
                        "severity": ErrorSeverity.ERROR,
                        "category": ErrorCategory.FORMAT,
                        "message": error_msg
                    })
            
            # Process warnings
            for warning_msg in issues.get('warnings', []):
                if not _is_duplicate_message(warning_msg, warnings):
                    warnings.append({
                        "severity": ErrorSeverity.WARNING,
                        "category": ErrorCategory.FORMAT,
                        "message": warning_msg
                    })
        else:
            # Fallback for version without warnings support
            if hasattr(las_file, 'get_non_conformities'):
                non_conformities = las_file.get_non_conformities()
                for error_msg in non_conformities:
                    # Classify as warning or error based on content
                    if _should_be_warning(error_msg):
                        if not _is_duplicate_message(error_msg, warnings):
                            warnings.append({
                                "severity": ErrorSeverity.WARNING,
                                "category": ErrorCategory.FORMAT,
                                "message": error_msg
                            })
                    else:
                        if not _is_duplicate_message(error_msg, errors):
                            errors.append({
                                "severity": ErrorSeverity.ERROR,
                                "category": ErrorCategory.FORMAT,
                                "message": error_msg
                            })
                            
    except Exception as e:
        # If the library doesn't support these methods, do manual validation
        manual_errors, manual_warnings = _manual_validation(las_file)
        errors.extend(manual_errors)
        warnings.extend(manual_warnings)
    
    return errors, warnings

def _manual_validation(las_file) -> Tuple[List[Dict], List[Dict]]:
    """Manual validation as fallback when library methods are not available"""
    errors = []
    warnings = []
    
    # Check mandatory sections
    mandatory_sections = ["Version", "Well", "Curves", "Ascii"]
    for section in mandatory_sections:
        if section not in las_file.sections:
            errors.append({
                "severity": ErrorSeverity.ERROR,
                "category": ErrorCategory.STRUCTURE,
                "message": f"Отсутствует обязательная секция ~{section[0].upper()}"
            })
    
    # Check for blank lines (as warning)
    if hasattr(las_file, 'sections_with_blank_line') and las_file.sections_with_blank_line:
        unique_sections = list(set(las_file.sections_with_blank_line))
        for section in unique_sections:
            warnings.append({
                "severity": ErrorSeverity.WARNING,
                "category": ErrorCategory.FORMAT,
                "message": f"Пустые строки в секции {section}"
            })
    
    # Check for duplicate sections
    if hasattr(las_file, 'duplicate_v_section') and las_file.duplicate_v_section:
        errors.append({
            "severity": ErrorSeverity.ERROR,
            "category": ErrorCategory.STRUCTURE,
            "message": "Дублирующаяся секция ~V"
        })
    
    # Check section order
    if hasattr(las_file, 'v_section_first') and not las_file.v_section_first:
        errors.append({
            "severity": ErrorSeverity.ERROR,
            "category": ErrorCategory.STRUCTURE,
            "message": "Секция ~V должна быть первой"
        })
    
    # Check sections after ~A
    if hasattr(las_file, 'sections_after_a_section') and las_file.sections_after_a_section:
        errors.append({
            "severity": ErrorSeverity.ERROR,
            "category": ErrorCategory.STRUCTURE,
            "message": "Обнаружены секции после секции ~A"
        })
    
    return errors, warnings

def _should_be_warning(message: str) -> bool:
    """Determine if a message should be a warning rather than an error"""
    warning_keywords = [
        'blank line', 'пустые строки', 'пустая строка',
        'recommended', 'рекомендуется', 'suggestion',
        'warning', 'предупреждение'
    ]
    return any(keyword in message.lower() for keyword in warning_keywords)

def _is_duplicate_message(message: str, existing_list: List[Dict]) -> bool:
    """Check if a message already exists in the list"""
    for item in existing_list:
        if item.get("message") == message:
            return True
    return False

def _collect_statistics(las_file) -> Dict[str, Any]:
    """Collect statistics about the LAS file"""
    stats = {}
    
    # Curve statistics
    if "Curves" in las_file.sections:
        curves = las_file.curves
        stats["curve_count"] = len(curves)
        stats["curve_names"] = [c.mnemonic for c in curves]
        
        # Check for duplicate curves
        curve_names = [c.mnemonic for c in curves]
        duplicates = [name for name in curve_names if curve_names.count(name) > 1]
        if duplicates:
            stats["duplicate_curves"] = list(set(duplicates))
    
    # Well information statistics
    if "Well" in las_file.sections:
        well_info = las_file.well
        stats["well_parameters_count"] = len(well_info)
        
        # Check depth range
        if "STRT" in well_info and "STOP" in well_info:
            try:
                start = float(well_info["STRT"].value)
                stop = float(well_info["STOP"].value)
                stats["depth_range"] = f"{start} - {stop} {well_info['STRT'].unit}"
            except (ValueError, TypeError):
                pass
    
    # Version information
    if "Version" in las_file.sections:
        version_info = las_file.version
        if "VERS" in version_info:
            stats["las_version"] = version_info["VERS"].value
        if "WRAP" in version_info:
            stats["wrap_mode"] = version_info["WRAP"].value
    
    return stats

def _collect_info(las_file) -> List[str]:
    """Collect informational messages about the LAS file"""
    info = []
    
    # Well information
    if "Well" in las_file.sections:
        well_info = las_file.well
        
        if "WELL" in well_info and well_info["WELL"].value:
            info.append(f"Скважина: {well_info['WELL'].value}")
        
        if "FLD" in well_info and well_info["FLD"].value:
            info.append(f"Месторождение: {well_info['FLD'].value}")
        
        if "COMP" in well_info and well_info["COMP"].value:
            info.append(f"Компания: {well_info['COMP'].value}")
        
        if "DATE" in well_info and well_info["DATE"].value:
            info.append(f"Дата: {well_info['DATE'].value}")
        
        if "LOC" in well_info and well_info["LOC"].value:
            info.append(f"Местоположение: {well_info['LOC'].value}")
        
        if "SRVC" in well_info and well_info["SRVC"].value:
            info.append(f"Сервисная компания: {well_info['SRVC'].value}")
    
    # Version information
    if "Version" in las_file.sections:
        version_info = las_file.version
        if "VERS" in version_info:
            info.append(f"Версия LAS: {version_info['VERS'].value}")
        
    return info


def _generate_summary(errors: List[Dict], warnings: List[Dict]) -> str:
    """Generate a summary message"""
    critical_count = len([e for e in errors if e["severity"] == ErrorSeverity.CRITICAL])
    error_count = len([e for e in errors if e["severity"] == ErrorSeverity.ERROR])
    warning_count = len(warnings)
    
    if critical_count > 0:
        return f"Файл содержит критические ошибки ({critical_count}) и не может быть обработан."
    elif error_count > 0:
        return f"Файл проверен. Обнаружено ошибок: {error_count}, предупреждений: {warning_count}."
    else:
        return f"Файл полностью соответствует стандарту LAS 2.0."

def _format_error(error: Dict) -> str:
    """Format error for display"""
    if isinstance(error, str):
        return error
    return error.get("message", str(error))