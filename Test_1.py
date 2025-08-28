import lascheck
from typing import Dict, List, Union, Any


def validate_las_file(file_path: str, **kwargs) -> Dict[str, Any]:
    """
    Validate a LAS file and return structured results.  
    
    Args:
        file_path (str): Path to the LAS file to validate
        **kwargs: Additional arguments to pass to lascheck.read()
    
    Returns:
        Dict containing:
        - summary: General summary message
        - errors: List of validation errors found
        - valid: Boolean indicating if file is valid (no errors)
    """
    errors = []
    
    try:
        # Read the LAS file
        las_file = lascheck.read(file_path, **kwargs)
        
        # Get all non-conformities (errors)
        non_conformities = las_file.get_non_conformities()
        
        # Convert non-conformities to error list
        errors.extend(non_conformities)
        
        # Check for additional validation issues
        try:
            # Check if file has mandatory sections
            if not las_file.check_conformity():
                # This is a backup check, most issues should be caught by get_non_conformities()
                if not errors:  # Only add if no specific errors were found
                    errors.append("File does not conform to LAS specification")
        except Exception as e:
            errors.append(f"Error during conformity check: {str(e)}")
            
    except FileNotFoundError:
        errors.append(f"File not found: {file_path}")
    except Exception as e:
        errors.append(f"Error reading LAS file: {str(e)}")
    
    # Prepare results
    results = {
        "summary": "Файл проверен",
        "errors": errors,
        "valid": len(errors) == 0
    }
    
    return results


def validate_las_file_detailed(file_path: str, **kwargs) -> Dict[str, Any]:
    """
    Validate a LAS file with more detailed error categorization.
    
    Args:
        file_path (str): Path to the LAS file to validate
        **kwargs: Additional arguments to pass to lascheck.read()
    
    Returns:
        Dict containing detailed validation results
    """
    errors = []
    warnings = []
    info = []
    
    try:
        # Read the LAS file
        las_file = lascheck.read(file_path, **kwargs)
        
        # Get basic file information
        try:
            version = las_file.version["VERS"].value if "VERS" in las_file.version else "Unknown"
            info.append(f"LAS version: {version}")
        except:
            warnings.append("Could not determine LAS version")
        
        try:
            well_name = las_file.well["WELL"].value if "WELL" in las_file.well else "Unknown"
            info.append(f"Well name: {well_name}")
        except:
            pass
        
        # Get all non-conformities
        non_conformities = las_file.get_non_conformities()
        
        # Categorize errors by severity
        for error in non_conformities:
            error_lower = error.lower()
            if any(keyword in error_lower for keyword in ['missing mandatory', 'invalid index mnemonic']):
                errors.append(error)
            elif any(keyword in error_lower for keyword in ['duplicate', 'blank line']):
                warnings.append(error)
            else:
                errors.append(error)  # Default to error for unknown issues
        
        # Additional checks
        try:
            if hasattr(las_file, 'curves') and len(las_file.curves) == 0:
                errors.append("No curves found in file")
        except:
            pass
            
    except FileNotFoundError:
        errors.append(f"File not found: {file_path}")
    except lascheck.exceptions.LASHeaderError as e:
        errors.append(f"LAS header error: {str(e)}")
    except lascheck.exceptions.LASDataError as e:
        errors.append(f"LAS data error: {str(e)}")
    except Exception as e:
        errors.append(f"Unexpected error reading LAS file: {str(e)}")
    
    # Combine all issues into errors list for the required format
    all_errors = errors + warnings
    
    # Prepare results in the requested format
    results = {
        "summary": "Файл проверен",
        "errors": all_errors,
        "valid": len(all_errors) == 0
    }
    
    # Add extra info for debugging (optional)
    if info:
        results["info"] = info
    
    return results


def validate_las_files_batch(file_paths: List[str], **kwargs) -> Dict[str, Dict[str, Any]]:
    """
    Validate multiple LAS files.
    
    Args:
        file_paths (List[str]): List of paths to LAS files
        **kwargs: Additional arguments to pass to lascheck.read()
    
    Returns:
        Dict with file paths as keys and validation results as values
    """
    results = {}
    
    for file_path in file_paths:
        results[file_path] = validate_las_file(file_path, **kwargs)
    
    return results


# # Example usage
# if __name__ == "__main__":
#     # Example validation
#     file_path = "example.las"  # Replace with your LAS file path
    
#     # Basic validation
#     result = validate_las_file(file_path)
#     print("Validation Result:")
#     print(f"Summary: {result['summary']}")
#     print(f"Valid: {result['valid']}")
#     print(f"Errors: {result['errors']}")
    
#     # Detailed validation
#     detailed_result = validate_las_file_detailed(file_path)
#     print("\nDetailed Validation Result:")
#     print(f"Summary: {detailed_result['summary']}")
#     print(f"Valid: {detailed_result['valid']}")
#     print(f"Errors: {detailed_result['errors']}")
#     if 'info' in detailed_result:
#         print(f"Info: {detailed_result['info']}")