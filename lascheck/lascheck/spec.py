import re

class Rule:
    pass


class WellSectionExists(Rule):
    @staticmethod
    def check(las_file):
        return "Well" in las_file.sections


class VersionSectionExists(Rule):
    @staticmethod
    def check(las_file):
        return "Version" in las_file.sections


class CurvesSectionExists(Rule):
    @staticmethod
    def check(las_file):
        return "Curves" in las_file.sections


class AsciiSectionExists(Rule):
    @staticmethod
    def check(las_file):
        return "Ascii" in las_file.sections


class MandatorySections(Rule):
    @staticmethod
    def check(las_file):
        return VersionSectionExists.check(las_file) and \
               WellSectionExists.check(las_file) and \
               CurvesSectionExists.check(las_file) and \
               AsciiSectionExists.check(las_file)

    @staticmethod
    def get_missing_mandatory_sections(las_file):
        missing_mandatory_sections = []
        if "Version" not in las_file.sections:
            missing_mandatory_sections.append("~V")
        if "Well" not in las_file.sections:
            missing_mandatory_sections.append("~W")
        if "Curves" not in las_file.sections:
            missing_mandatory_sections.append("~C")
        if "Ascii" not in las_file.sections:
            missing_mandatory_sections.append("~A")
        return missing_mandatory_sections


class MandatoryLinesInVersionSection(Rule):
    @staticmethod
    def check(las_file):
        if "Version" in las_file.sections:
            mandatory_lines = ["VERS", "WRAP"]
            return all(elem in las_file.version for elem in mandatory_lines)
        return False


class MandatoryLinesInWellSection(Rule):
    @staticmethod
    def check(las_file):
        if "Well" in las_file.sections:
            # PROV, UWI can have alternatives
            mandatory_lines = ["STRT", "STOP", "STEP", "NULL", "COMP", "WELL", "FLD", "LOC", "SRVC", "DATE"]
            mandatory_sections_found = all(elem in las_file.well for elem in mandatory_lines)
            if not mandatory_sections_found:
                return False
            if "UWI" not in las_file.well and "API" not in las_file.well:
                return False
            if "PROV" not in las_file.well and \
               "CNTY" not in las_file.well and \
               "CTRY" not in las_file.well and \
               "STAT" not in las_file.well:
                return False
            return True
        return False


class DuplicateSections(Rule):
    @staticmethod
    def check(las_file):
        if las_file.duplicate_v_section or \
                las_file.duplicate_w_section or \
                las_file.duplicate_p_section or \
                las_file.duplicate_c_section or \
                las_file.duplicate_o_section or \
                las_file.sections_after_a_section:
            return False
        else:
            return True


class ValidIndexMnemonic(Rule):
    @staticmethod
    def check(las_file):
        if "Curves" in las_file.sections:
            if las_file.curves[0].mnemonic == "DEPT" or \
                    las_file.curves[0].mnemonic == "DEPTH" or \
                    las_file.curves[0].mnemonic == "TIME" or \
                    las_file.curves[0].mnemonic == "INDEX":
                return True
        return False


class ValidUnitForDepth(Rule):
    @staticmethod
    def check(las_file):
        if "Curves" in las_file.sections and "Well" in las_file.sections and 'STRT' in las_file.well and \
                'STOP' in las_file.well and 'STEP' in las_file.well:
            if (las_file.curves[0].mnemonic == "DEPT" or
                    las_file.curves[0].mnemonic == "DEPTH"):
                index_unit = las_file.curves[0].unit
                return (index_unit == 'M' or index_unit == 'F' or index_unit == 'FT') \
                    and las_file.well['STRT'].unit == index_unit and las_file.well['STOP'].unit == index_unit and \
                    las_file.well['STEP'].unit == index_unit
            return True
        return True


class VSectionFirst(Rule):
    @staticmethod
    def check(las_file):
        return las_file.v_section_first


class BlankLineInSection(Rule):
    @staticmethod
    def check(las_file):
        if las_file.blank_line_in_section:
            return False
        return True


# NEW RULES FOR SPECIAL CHARACTER VALIDATION

class ValidMnemonicCharacters(Rule):
    """
    Check that mnemonics only contain valid characters.
    According to LAS 2.0 spec, mnemonics should only contain:
    - Letters (A-Z, a-z)
    - Numbers (0-9)
    - Underscore (_)
    - Hyphen/dash (-)
    - Period (.) - sometimes used for units or sub-properties
    """
    
    # Pattern for valid mnemonic characters
    VALID_PATTERN = re.compile(r'^[A-Za-z0-9_\-\.]+$')
    
    # Pattern for problematic special characters
    SPECIAL_CHARS_PATTERN = re.compile(r'[#@!$%^&*()\[\]{};:"\'<>?\\|`~+=]')
    
    @staticmethod
    def check(las_file):
        """Check if all mnemonics contain only valid characters."""
        return (ValidMnemonicCharacters.check_curves(las_file) and
                ValidMnemonicCharacters.check_well_section(las_file) and
                ValidMnemonicCharacters.check_parameters(las_file))
    
    @staticmethod
    def check_curves(las_file):
        """Check curve mnemonics for invalid characters."""
        if "Curves" not in las_file.sections:
            return True
        
        for curve in las_file.curves:
            if not ValidMnemonicCharacters.VALID_PATTERN.match(curve.original_mnemonic):
                return False
        return True
    
    @staticmethod
    def check_well_section(las_file):
        """Check well section mnemonics for invalid characters."""
        if "Well" not in las_file.sections:
            return True
        
        for item in las_file.well:
            if not ValidMnemonicCharacters.VALID_PATTERN.match(item.mnemonic):
                return False
        return True
    
    @staticmethod
    def check_parameters(las_file):
        """Check parameter mnemonics for invalid characters."""
        if "Parameter" not in las_file.sections:
            return True
        
        for item in las_file.params:
            if not ValidMnemonicCharacters.VALID_PATTERN.match(item.mnemonic):
                return False
        return True
    
    @staticmethod
    def get_invalid_mnemonics(las_file):
        """Get list of all mnemonics with invalid characters."""
        invalid = []
        
        # Check curves
        if "Curves" in las_file.sections:
            for i, curve in enumerate(las_file.curves):
                if not ValidMnemonicCharacters.VALID_PATTERN.match(curve.original_mnemonic):
                    line_num = getattr(curve, 'line_number', None)
                    special_chars = ValidMnemonicCharacters.SPECIAL_CHARS_PATTERN.findall(curve.original_mnemonic)
                    invalid.append({
                        'section': '~C',
                        'index': i + 1,
                        'line_number': line_num,
                        'mnemonic': curve.original_mnemonic,
                        'special_chars': special_chars,
                        'type': 'curve'
                    })
        
        # Check well section
        if "Well" in las_file.sections:
            for item in las_file.well:
                if not ValidMnemonicCharacters.VALID_PATTERN.match(item.mnemonic):
                    line_num = getattr(item, 'line_number', None)
                    special_chars = ValidMnemonicCharacters.SPECIAL_CHARS_PATTERN.findall(item.mnemonic)
                    invalid.append({
                        'section': '~W',
                        'mnemonic': item.mnemonic,
                        'line_number': line_num,
                        'special_chars': special_chars,
                        'type': 'well'
                    })
        
        # Check parameters
        if "Parameter" in las_file.sections:
            for item in las_file.params:
                if not ValidMnemonicCharacters.VALID_PATTERN.match(item.mnemonic):
                    special_chars = ValidMnemonicCharacters.SPECIAL_CHARS_PATTERN.findall(item.mnemonic)
                    line_num = getattr(item, 'line_number', None)                    
                    invalid.append({
                        'section': '~P',
                        'mnemonic': item.mnemonic,
                        'line_number': line_num,                        
                        'special_chars': special_chars,
                        'type': 'parameter'
                    })
        
        return invalid


class NoHashInMnemonics(Rule):
    """
    Specific rule to check for # character in mnemonics.
    The # character is particularly problematic as it's often used for comments.
    """
    
    @staticmethod
    def check(las_file):
        """Check if any mnemonic contains the # character."""
        # Check curves
        if "Curves" in las_file.sections:
            for curve in las_file.curves:
                if '#' in curve.mnemonic:
                    return False
        
        # Check well section
        if "Well" in las_file.sections:
            for item in las_file.well:
                if '#' in item.mnemonic:
                    return False
        
        # Check parameters
        if "Parameter" in las_file.sections:
            for item in las_file.params:
                if '#' in item.mnemonic:
                    return False
        
        return True
    
    @staticmethod
    def get_mnemonics_with_hash(las_file):
        """Get list of all mnemonics containing # character."""
        mnemonics_with_hash = []
        
        # Check curves
        if "Curves" in las_file.sections:
            for i, curve in enumerate(las_file.curves):
                if '#' in curve.mnemonic:
                    line_num = getattr(curve, 'line_number', None)
                    mnemonics_with_hash.append({
                        'section': '~C',
                        'index': i + 1,
                        'line_number': line_num,                    
                        'mnemonic': curve.mnemonic,
                        'type': 'curve'
                    })
                    
        # Check well section
        if "Well" in las_file.sections:
            for item in las_file.well:
                if '#' in item.mnemonic:
                    line_num = getattr(item, 'line_number', None)
                    mnemonics_with_hash.append({
                        'section': '~W',
                        'line_number': line_num,
                        'mnemonic': item.mnemonic,
                        'type': 'well'
                    })
        
        # Check parameters
        if "Parameter" in las_file.sections:
            for item in las_file.params:
                if '#' in item.mnemonic:
                    line_num = getattr(item, 'line_number', None)
                    mnemonics_with_hash.append({
                        'section': '~P',
                        'line_number': line_num,
                        'mnemonic': item.mnemonic,
                        'type': 'parameter'
                    })
        
        return mnemonics_with_hash


class MnemonicStartsWithLetter(Rule):
    """
    Check that mnemonics start with a letter, not a number or special character.
    This is a best practice for most programming and data systems.
    """
    
    @staticmethod
    def check(las_file):
        """Check if all mnemonics start with a letter."""
        # Check curves
        if "Curves" in las_file.sections:
            for curve in las_file.curves:
                if curve.mnemonic and not curve.mnemonic[0].isalpha():
                    return False
        
        # Check well section
        if "Well" in las_file.sections:
            for item in las_file.well:
                if item.mnemonic and not item.mnemonic[0].isalpha():
                    return False
        
        # Check parameters
        if "Parameter" in las_file.sections:
            for item in las_file.params:
                if item.mnemonic and not item.mnemonic[0].isalpha():
                    return False
        
        return True
    
    @staticmethod
    def get_invalid_starting_mnemonics(las_file):
        """Get list of mnemonics that don't start with a letter."""
        invalid = []
        
        # Check curves
        if "Curves" in las_file.sections:
            for i, curve in enumerate(las_file.curves):
                if curve.mnemonic and not curve.mnemonic[0].isalpha():
                    invalid.append({
                        'section': '~C',
                        'index': i + 1,
                        'mnemonic': curve.mnemonic,
                        'first_char': curve.mnemonic[0],
                        'type': 'curve'
                    })
        
        # Check well section
        if "Well" in las_file.sections:
            for item in las_file.well:
                if item.mnemonic and not item.mnemonic[0].isalpha():
                    invalid.append({
                        'section': '~W',
                        'mnemonic': item.mnemonic,
                        'first_char': item.mnemonic[0],
                        'type': 'well'
                    })
        
        # Check parameters
        if "Parameter" in las_file.sections:
            for item in las_file.params:
                if item.mnemonic and not item.mnemonic[0].isalpha():
                    invalid.append({
                        'section': '~P',
                        'mnemonic': item.mnemonic,
                        'first_char': item.mnemonic[0],
                        'type': 'parameter'
                    })
        
        return invalid



class DuplicateCurves(Rule):
    """Check for duplicate curve mnemonics in the ~C section."""
    
    @staticmethod
    def check(las_file):
        """
        Check if there are duplicate curve mnemonics.
        Returns True if no duplicates, False if duplicates exist.
        """
        if "Curves" not in las_file.sections:
            return True
        
        curve_mnemonics = {}
        for curve in las_file.curves:
            original_mnemonic = curve.original_mnemonic
            if original_mnemonic in curve_mnemonics:
                return False  # Found a duplicate
            curve_mnemonics[original_mnemonic] = True
        
        return True
    
    @staticmethod
    def get_duplicate_curves_with_lines(las_file):
        """
        Get detailed information about duplicate curve mnemonics including line numbers.
        Returns a dictionary with mnemonics as keys and list of line numbers as values.
        """
        if "Curves" not in las_file.sections:
            return {}
        
        curve_info = {}
        duplicates = {}
        
        for curve in las_file.curves:
            original_mnemonic = curve.original_mnemonic
            line_num = getattr(curve, 'line_number', 'unknown')
            
            if original_mnemonic not in curve_info:
                curve_info[original_mnemonic] = []
            curve_info[original_mnemonic].append(line_num)
        
        # Filter to only keep duplicates
        for mnemonic, lines in curve_info.items():
            if len(lines) > 1:
                duplicates[mnemonic] = lines
        
        return duplicates