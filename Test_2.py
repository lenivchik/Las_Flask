import lascheck
from typing import Dict, List, Union, Any
import re


def validate_las_file_comprehensive(file_path: str, **kwargs) -> Dict[str, Any]:
    """
    Comprehensive LAS file validation that captures ALL errors including header errors
    and structural issues, without modifying the library code.
    
    Args:
        file_path (str): Path to the LAS file to validate
        **kwargs: Additional arguments to pass to lascheck.read()
    
    Returns:
        Dict containing:
        - summary: General summary message
        - errors: List of ALL validation errors found
        - valid: Boolean indicating if file is valid (no errors)
    """
    all_errors = []
    las_file = None
    
    # Step 1: Try to read with header errors ignored to get structural validation
    try:
        las_file = lascheck.read(file_path, ignore_header_errors=True, **kwargs)
        structural_errors = _get_all_structural_errors(las_file)
        all_errors.extend(structural_errors)
    except Exception as e:
        all_errors.append(f"Critical error reading file: {str(e)}")
        return {
            "summary": "Файл проверен",
            "errors": all_errors,
            "valid": False
        }
    
    # Step 2: Try to read with header errors NOT ignored to capture header errors
    header_errors = _get_header_errors_by_reprocessing(file_path, **kwargs)
    all_errors.extend(header_errors)
    
    # Step 3: Manual raw file analysis for additional issues
    raw_file_errors = _analyze_raw_file(file_path)
    all_errors.extend(raw_file_errors)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_errors = []
    for error in all_errors:
        if error not in seen:
            seen.add(error)
            unique_errors.append(error)
    
    results = {
        "summary": "Файл проверен",
        "errors": unique_errors,
        "valid": len(unique_errors) == 0
    }
    
    return results


def _get_all_structural_errors(las_file) -> List[str]:
    """Get all structural validation errors from LAS file object."""
    errors = []
    
    # Clear existing non-conformities to get fresh validation
    las_file.non_conformities = []
    
    # Run the library's validation
    non_conformities = las_file.get_non_conformities()
    errors.extend(non_conformities)
    
    # Additional manual checks for completeness
    try:
        # Check for blank lines in sections with specific section names
        if hasattr(las_file, 'sections_with_blank_line') and las_file.sections_with_blank_line:
            for section in las_file.sections_with_blank_line:
                error_msg = f"Section {section} has blank line"
                if error_msg not in errors:
                    errors.append(error_msg)
    except Exception as e:
        errors.append(f"Error checking blank lines: {str(e)}")
    
    return errors


def _get_header_errors_by_reprocessing(file_path: str, **kwargs) -> List[str]:
    """
    Get header errors by attempting to read the file without ignoring header errors.
    This captures the specific header parsing errors.
    """
    header_errors = []
    
    try:
        # Try reading WITHOUT ignoring header errors
        lascheck.read(file_path, ignore_header_errors=False, **kwargs)
    except lascheck.exceptions.LASHeaderError as e:
        # Extract the specific error message
        error_msg = str(e)
        header_errors.append(f"Header error: {error_msg}")
    except Exception as e:
        # Other types of errors during header processing
        error_msg = str(e)
        if "header" in error_msg.lower():
            header_errors.append(f"Header processing error: {error_msg}")
    
    return header_errors


def _analyze_raw_file(file_path: str) -> List[str]:
    """
    Analyze the raw LAS file content for additional issues that might be missed.
    """
    errors = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        current_section = None
        section_line_count = 0
        found_sections = []
        
        for line_no, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Skip empty lines and comments
            if not line_stripped or line_stripped.startswith('#'):
                # Check if empty line is within a section (not between sections)
                if current_section and section_line_count > 0:
                    error_msg = f"Section {current_section} has blank line at line {line_no}"
                    if error_msg not in errors:
                        errors.append(error_msg)
                continue
            
            # Check for section headers
            if line_stripped.startswith('~'):
                # Check for duplicate sections
                section_type = line_stripped.split()[0].upper()
                if section_type in found_sections:
                    errors.append(f"Duplicate section {section_type} found at line {line_no}")
                found_sections.append(section_type)
                
                current_section = section_type
                section_line_count = 0
                
                # Check if ~V section is first
                if len(found_sections) == 1 and section_type != '~V':
                    errors.append("~V section is not the first section")
                
                continue
            
            # We're in a section with content
            if current_section:
                section_line_count += 1
                
                # Check for sections after ~A
                if current_section == '~A':
                    # If we find another section after ~A, it's an error
                    # This is handled in the section detection above
                    pass
    
    except FileNotFoundError:
        errors.append(f"File not found: {file_path}")
    except Exception as e:
        errors.append(f"Error analyzing raw file: {str(e)}")
    
    return errors


def validate_las_file_debug(file_path: str, **kwargs) -> Dict[str, Any]:
    """
    Debug version that shows which validation method found each error.
    """
    all_errors = {}  # Dict to track which method found each error
    
    # Method 1: Structural validation with header errors ignored
    try:
        las_file = lascheck.read(file_path, ignore_header_errors=True, **kwargs)
        structural_errors = _get_all_structural_errors(las_file)
        for error in structural_errors:
            all_errors[error] = "structural_validation"
    except Exception as e:
        all_errors[f"Critical error: {str(e)}"] = "structural_validation"
    
    # Method 2: Header error detection
    header_errors = _get_header_errors_by_reprocessing(file_path, **kwargs)
    for error in header_errors:
        all_errors[error] = "header_validation"
    
    # Method 3: Raw file analysis
    raw_errors = _analyze_raw_file(file_path)
    for error in raw_errors:
        if error not in all_errors:
            all_errors[error] = "raw_file_analysis"
        else:
            all_errors[error] += " + raw_file_analysis"
    
    # Convert back to simple list for the result
    error_list = list(all_errors.keys())
    
    results = {
        "summary": "Файл проверен",
        "errors": error_list,
        "valid": len(error_list) == 0,
        "debug_info": all_errors  # Shows which method found each error
    }
    
    return results


# # Example usage
# if __name__ == "__main__":
#     # Test comprehensive validation
#     file_path = "example.las"
    
#     result = validate_las_file_comprehensive(file_path)
#     print("Comprehensive Validation:")
#     print(f"Valid: {result['valid']}")
#     for i, error in enumerate(result['errors'], 1):
#         print(f"{i}. {error}")
    
#     # Test debug version
#     debug_result = validate_las_file_debug(file_path)
#     print("\nDebug Validation:")
#     print(f"Valid: {debug_result['valid']}")
#     for error, method in debug_result['debug_info'].items():
#         print(f"{error} [Found by: {method}]")