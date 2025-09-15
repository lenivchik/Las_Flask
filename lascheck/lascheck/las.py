from __future__ import print_function

# Standard library packages
import json
import logging
import re

# get basestring in py3
try:
    unicode = unicode
except NameError:
    # 'unicode' is undefined, must be Python 3
    unicode = str
    basestring = (str, bytes)
else:
    # 'unicode' exists, must be Python 2
    bytes = str

# internal lascheck imports
from . import exceptions
from .las_items import HeaderItem, CurveItem, SectionItems, OrderedDict
from . import defaults
from . import reader
from . import spec

logger = logging.getLogger(__name__)

ERROR_MESSAGES = {
    "No ~ sections found. Is this a LAS file?": "Не найдены секции (~). Это действительно LAS-файл?",
    "Duplicate v section": "Дублирующаяся секция ~V",
    "Duplicate w section": "Дублирующаяся секция ~W",
    "Duplicate c section": "Дублирующаяся секция ~C",
    "Duplicate p section": "Дублирующаяся секция ~P",
    "Duplicate o section": "Дублирующаяся секция ~O",
    "Missing mandatory sections": "Отсутствуют обязательные секции",
    "Missing mandatory lines in ~v Section": "Отсутствуют обязательные строки в секции ~V",
    "Missing mandatory lines in ~w Section": "Отсутствуют обязательные строки в секции ~W",
    "Invalid index mnemonic. The only valid mnemonics for the index channel are DEPT, DEPTH, TIME, or INDEX.":
        "Некорректный индексный мнемоник. Допустимые: DEPT, DEPTH, TIME или INDEX.",
    "~v section not first": "Секция ~V должна идти первой",
    "Sections after ~a section": "После секции ~A обнаружены другие секции",
    "If the index is depth, the units must be M (metres), F (feet) or FT (feet)":
        "Если индекс — глубина, единицы измерения должны быть M (метры), F или FT (футы)",
    "NULL item not found in the ~W section": "Элемент NULL не найден в секции ~W",
    "VERS item not found in the ~V section.": "Элемент VERS не найден в секции ~V",
    "WRAP item not found in the ~V section": "Элемент WRAP не найден в секции ~V",
    "Header error in": "Ошибка заголовка в",
    "Section having blank line": "Пустые строки в секции",
    "Invalid characters in mnemonic": "Недопустимые символы в мнемонике",
    "Hash character (#) in mnemonic": "Символ решётка (#) в мнемонике",
    "Mnemonic does not start with letter": "Мнемоника не начинается с буквы",
    "Duplicate curve mnemonics found": "Обнаружены дублирующиеся мнемоники кривых",

}

def tr(msg):
    for eng, rus in ERROR_MESSAGES.items():
        if msg.startswith(eng):
            return msg.replace(eng, rus)
    return ERROR_MESSAGES.get(msg, msg)


class LASFile(object):
    """LAS file object.

    Keyword Arguments:
        file_ref (file-like object, str): either a filename, an open file
            object, or a string containing the contents of a file.

    See these routines for additional keyword arguments you can use when
    reading in a LAS file:

    * :func:`lascheck.reader.open_with_codecs` - manage issues relate to character
      encodings
    * :meth:`lascheck.las.LASFile.read` - control how NULL values and errors are
      handled during parsing

    Attributes:
        encoding (str or None): the character encoding used when reading the
            file in from disk

    """

    def __init__(self, file_ref=None, **read_kwargs):
        super(LASFile, self).__init__()
        self._text = ""
        self.index_unit = None
        self.non_conformities = []
        self.duplicate_v_section = False
        self.duplicate_w_section = False
        self.duplicate_p_section = False
        self.duplicate_c_section = False
        self.duplicate_o_section = False
        self.sections_after_a_section = False
        self.v_section_first = False
        self.blank_line_in_section = False
        self.sections_with_blank_line = []
        self.non_conforming_depth = []
        self.duplicate_curves = []
        
        # New attributes for special character tracking
        self.invalid_mnemonics = []
        self.mnemonics_with_hash = []
        self.mnemonics_with_invalid_start = []
        
        default_items = defaults.get_default_items()
        if not (file_ref is None):
            self.sections = {}
            self.read(file_ref, **read_kwargs)
        else:
            self.sections = {
                "Version": default_items["Version"],
                "Well": default_items["Well"],
                "Curves": default_items["Curves"],
                "Parameter": default_items["Parameter"],
                "Other": str(default_items["Other"]),
            }

    def read(
        self,
        file_ref,
        ignore_data=False,
        read_policy="default",
        null_policy="strict",
        ignore_header_errors=False,
        mnemonic_case="upper",
        index_unit=None,
        **kwargs
    ):
        """Read a LAS file.

        Arguments:
            file_ref (file-like object, str): either a filename, an open file
                object, or a string containing the contents of a file.

        Keyword Arguments:
            null_policy (str or list): see
                http://lascheck.readthedocs.io/en/latest/data-section.html#handling-invalid-data-indicators-automatically
            ignore_data (bool): if True, do not read in any of the actual data,
                just the header metadata. False by default.
            ignore_header_errors (bool): ignore LASHeaderErrors (False by
                default)
            mnemonic_case (str): 'preserve': keep the case of HeaderItem mnemonics
                                 'upper': convert all HeaderItem mnemonics to uppercase
                                 'lower': convert all HeaderItem mnemonics to lowercase
            index_unit (str): Optionally force-set the index curve's unit to "m" or "ft"

        See :func:`lascheck.reader.open_with_codecs` for additional keyword
        arguments which help to manage issues relate to character encodings.

        """

        file_obj, self.encoding = reader.open_file(file_ref, **kwargs)

        regexp_subs, value_null_subs, version_NULL = reader.get_substitutions(
            read_policy, null_policy
        )

        try:
            self.raw_sections, self.sections_after_a_section, self.v_section_first, self.blank_line_in_section, \
            self.sections_with_blank_line = \
                reader.read_file_contents(file_obj, regexp_subs, value_null_subs, ignore_data=ignore_data)
        finally:
            if hasattr(file_obj, "close"):
                file_obj.close()

        if len(self.raw_sections) == 0:
            raise KeyError(tr("No ~ sections found. Is this a LAS file?"))

        def add_section(pattern, name, **sect_kws):
            raw_section = self.match_raw_section(pattern)
            drop = []
            if raw_section:
                self.sections[name] = reader.parse_header_section(
                    raw_section, **sect_kws
                )
                drop.append(raw_section["title"])
            else:
                logger.warning(tr(f"Header section {name} regexp={pattern} was not found."))

            for key in drop:
                self.raw_sections.pop(key)

        def add_special_section(pattern, name, **sect_kws):
            raw_section = self.match_raw_section(pattern)
            drop = []
            if raw_section:
                self.sections[name] = "\n".join(raw_section["lines"])
                drop.append(raw_section["title"])
            else:
                logger.warning(tr(f"Header section {name} regexp={pattern} was not found."))

            for key in drop:
                self.raw_sections.pop(key)

        add_section(
            "~V",
            "Version",
            version=1.2,
            ignore_header_errors=ignore_header_errors,
            mnemonic_case=mnemonic_case,
        )

        if self.match_raw_section("~V"):
            self.duplicate_v_section = True
            self.non_conformities.append(tr("Duplicate v section"))

        # Establish version and wrap values if possible.
        try:
            version = self.version["VERS"].value
        except KeyError:
            logger.warning(tr("VERS item not found in the ~V section."))
            version = None

        try:
            wrap = self.version["WRAP"].value
        except KeyError:
            logger.warning(tr("WRAP item not found in the ~V section"))
            wrap = None

        # Validate version.
        try:
            assert version in (1.2, 2, None)
        except AssertionError:
            if version < 2:
                version = 1.2
            else:
                version = 2
        else:
            if version is None:
                logger.info("Assuming that LAS VERS is 2.0")
                version = 2

        add_section(
            "~W",
            "Well",
            version=version,
            ignore_header_errors=ignore_header_errors,
            mnemonic_case=mnemonic_case,
        )

        if self.match_raw_section("~W"):
            self.duplicate_w_section = True
            self.non_conformities.append(tr("Duplicate w section"))

        # Establish NULL value if possible.
        try:
            null = self.well["NULL"].value
        except KeyError:
            logger.warning(tr("NULL item not found in the ~W section"))
            null = None

        add_section(
            "~C",
            "Curves",
            version=version,
            ignore_header_errors=ignore_header_errors,
            mnemonic_case=mnemonic_case,
        )

        if self.match_raw_section("~C"):
            self.duplicate_c_section = True
            self.non_conformities.append(tr("Duplicate c section"))

        add_section(
            "~P",
            "Parameter",
            version=version,
            ignore_header_errors=ignore_header_errors,
            mnemonic_case=mnemonic_case,
        )

        if self.match_raw_section("~P"):
            self.duplicate_p_section = True
            self.non_conformities.append(tr("Duplicate p section"))

        add_special_section("~A", "Ascii")

        add_special_section("~O", "Other")
        if self.match_raw_section("~O"):
            self.duplicate_o_section = True
            self.non_conformities.append(tr("Duplicate o section"))

        # Deal with nonstandard sections
        drop = []
        for s in self.raw_sections.values():
            if s["section_type"] == "header":
                logger.warning(tr("Found nonstandard LAS section: ") + s["title"])
                self.sections[s["title"][1:]] = "\n".join(s["lines"])
                drop.append(s["title"])
        for key in drop:
            self.raw_sections.pop(key)

        if "m" in str(index_unit):
            index_unit = "m"

        if index_unit:
            self.index_unit = index_unit
        else:
            check_units_on = []
            for mnemonic in ("STRT", "STOP", "STEP"):
                if "Well" in self.sections:
                    if mnemonic in self.well:
                        check_units_on.append(self.well[mnemonic])
            if "Curves" in self.sections:
                if len(self.curves) > 0:
                    check_units_on.append(self.curves[0])
            for index_unit, possibilities in defaults.DEPTH_UNITS.items():
                if all(i.unit.upper() in possibilities for i in check_units_on):
                    self.index_unit = index_unit

    def match_raw_section(self, pattern, re_func="match", flags=re.IGNORECASE):
        """Find raw section with a regular expression."""
        for title in self.raw_sections.keys():
            title = title.strip()
            p = re.compile(pattern, flags=flags)
            if re_func == "match":
                re_func = re.match
            elif re_func == "search":
                re_func = re.search
            m = re_func(p, title)
            if m:
                return self.raw_sections[title]

    def get_curve(self, mnemonic):
        """Return CurveItem object."""
        for curve in self.curves:
            if curve.mnemonic == mnemonic:
                return curve

    def __getitem__(self, key):
        """Provide access to curve data."""
        curve_mnemonics = [c.mnemonic for c in self.curves]
        if isinstance(key, int):
            return self.curves[key].data
        elif key in curve_mnemonics:
            return self.curves[key].data
        else:
            raise KeyError("{} not found in curves ({})".format(key, curve_mnemonics))

    def __setitem__(self, key, value):
        """Append a curve."""
        if isinstance(value, CurveItem):
            if key != value.mnemonic:
                raise KeyError(
                    "key {} does not match value.mnemonic {}".format(
                        key, value.mnemonic
                    )
                )
            self.append_curve_item(value)
        else:
            # Assume value is an ndarray
            self.append_curve(key, value)

    def keys(self):
        """Return curve mnemonics."""
        return [c.mnemonic for c in self.curves]

    def values(self):
        """Return data for each curve."""
        return [c.data for c in self.curves]

    def items(self):
        """Return mnemonics and data for all curves."""
        return [(c.mnemonic, c.data) for c in self.curves]

    def iterkeys(self):
        return iter(list(self.keys()))

    def itervalues(self):
        return iter(list(self.values()))

    def iteritems(self):
        return iter(list(self.items()))

    @property
    def version(self):
        """Header information from the Version (~V) section."""
        return self.sections["Version"]

    @version.setter
    def version(self, section):
        self.sections["Version"] = section

    @property
    def well(self):
        """Header information from the Well (~W) section."""
        return self.sections["Well"]

    @well.setter
    def well(self, section):
        self.sections["Well"] = section

    @property
    def curves(self):
        """Curve information and data from the Curves (~C) and data section."""
        return self.sections["Curves"]

    @curves.setter
    def curves(self, section):
        self.sections["Curves"] = section

    @property
    def curvesdict(self):
        """Curve information and data from the Curves (~C) and data section."""
        d = {}
        for curve in self.curves:
            d[curve["mnemonic"]] = curve
        return d

    @property
    def params(self):
        """Header information from the Parameter (~P) section."""
        return self.sections["Parameter"]

    @params.setter
    def params(self, section):
        self.sections["Parameter"] = section

    @property
    def other(self):
        """Header information from the Other (~O) section."""
        return self.sections["Other"]

    @other.setter
    def other(self, section):
        self.sections["Other"] = section

    @property
    def metadata(self):
        """All header information joined together."""
        s = SectionItems()
        for section in self.sections:
            for item in section:
                s.append(item)
        return s

    @metadata.setter
    def metadata(self, value):
        raise NotImplementedError("Set values in the section directly")

    @property
    def header(self):
        """All header information"""
        return self.sections

    @property
    def data(self):
        import numpy as np
        return np.vstack([c.data for c in self.curves]).T

    @data.setter
    def data(self, value):
        return self.set_data(value)

    def set_data(self, array_like, names=None, truncate=False):
        """Set the data for the LAS; actually sets data on individual curves."""
        try:
            import pandas as pd
        except ImportError:
            pass
        else:
            if isinstance(array_like, pd.DataFrame):
                return self.set_data_from_df(
                    array_like, **dict(names=names, truncate=False)
                )
        data = array_like

        # Truncate data array if necessary.
        if truncate:
            data = data[:, len(self.curves)]

        # Extend curves list if necessary.
        while data.shape[1] > len(self.curves):
            self.curves.append(CurveItem(""))

        if not names:
            names = [c.original_mnemonic for c in self.curves]
        else:
            # Extend names list if necessary.
            while len(self.curves) > len(names):
                names.append("")
        logger.debug("set_data. names to use: {}".format(names))

        for i, curve in enumerate(self.curves):
            curve.mnemonic = names[i]
            curve.data = data[:, i]

        self.curves.assign_duplicate_suffixes()

    @property
    def index(self):
        """Return data from the first column of the LAS file data (depth/time)."""
        return self.curves[0].data

    @property
    def depth_m(self):
        """Return the index as metres."""
        if self._index_unit_contains("M"):
            return self.index
        elif self._index_unit_contains("F"):
            return self.index * 0.3048
        else:
            raise exceptions.LASUnknownUnitError("Unit of depth index not known")

    @property
    def depth_ft(self):
        """Return the index as feet."""
        if self._index_unit_contains("M"):
            return self.index / 0.3048
        elif self._index_unit_contains("F"):
            return self.index
        else:
            raise exceptions.LASUnknownUnitError("Unit of depth index not known")

    def _index_unit_contains(self, unit_code):
        """Check value of index_unit string, ignoring case"""
        return self.index_unit and (unit_code.upper() in self.index_unit.upper())

    def add_curve_raw(self, mnemonic, data, unit="", descr="", value=""):
        """Deprecated. Use append_curve_item() or insert_curve_item() instead."""
        return self.append_curve_item(self, mnemonic, data, unit, descr, value)

    def append_curve_item(self, curve_item):
        """Add a CurveItem."""
        self.insert_curve_item(len(self.curves), curve_item)

    def insert_curve_item(self, ix, curve_item):
        """Insert a CurveItem."""
        assert isinstance(curve_item, CurveItem)
        self.curves.insert(ix, curve_item)

    def add_curve(self, *args, **kwargs):
        """Deprecated. Use append_curve() or insert_curve() instead."""
        return self.append_curve(*args, **kwargs)

    def append_curve(self, mnemonic, data, unit="", descr="", value=""):
        """Add a curve."""
        return self.insert_curve(len(self.curves), mnemonic, data, unit, descr, value)

    def insert_curve(self, ix, mnemonic, data, unit="", descr="", value=""):
        """Insert a curve."""
        curve = CurveItem(mnemonic, unit, value, descr, data)
        self.insert_curve_item(ix, curve)

    def delete_curve(self, mnemonic=None, ix=None):
        """Delete a curve."""
        if ix is None:
            ix = self.curves.keys().index(mnemonic)
        self.curves.pop(ix)

    @property
    def json(self):
        """Return object contents as a JSON string."""
        obj = OrderedDict()
        for name, section in self.sections.items():
            try:
                obj[name] = section.json
            except AttributeError:
                obj[name] = json.dumps(section)
        return json.dumps(obj)

    @json.setter
    def json(self, value):
        raise Exception("Cannot set objects from JSON")

    def check_conformity(self):
        """Check conformity to LAS 2.0 specification including special characters."""
        return (spec.MandatorySections.check(self) and 
                spec.MandatoryLinesInVersionSection.check(self) and 
                spec.MandatoryLinesInWellSection.check(self) and 
                spec.DuplicateSections.check(self) and 
                spec.ValidIndexMnemonic.check(self) and 
                spec.VSectionFirst.check(self) and 
                spec.BlankLineInSection.check(self) and 
                spec.ValidUnitForDepth.check(self) and
                spec.ValidMnemonicCharacters.check(self) and  # NEW
                spec.NoHashInMnemonics.check(self) and  # NEW
                spec.MnemonicStartsWithLetter.check(self) and   # NEW
                spec.DuplicateCurves.check(self)) # NEW
    

    def get_non_conformities(self):
        """Get all non-conformities including special character issues."""
        # Standard conformity checks
        if (spec.MandatorySections.check(self)) is False:
            self.non_conformities.append(tr("Missing mandatory sections: {}".format(
                spec.MandatorySections.get_missing_mandatory_sections(self))))
        
        if ("Version" in self.sections) and (spec.MandatoryLinesInVersionSection.check(self)) is False:
            self.non_conformities.append(tr("Missing mandatory lines in ~v Section"))
        
        if (spec.MandatoryLinesInWellSection.check(self)) is False:
            self.non_conformities.append(tr("Missing mandatory lines in ~w Section"))
        
        if ('Curves' in self.sections) and (spec.ValidIndexMnemonic.check(self)) is False:
            self.non_conformities.append(tr("Invalid index mnemonic. "
                                         "The only valid mnemonics for the index channel are DEPT, DEPTH, TIME, or INDEX."))
        
        if (spec.VSectionFirst.check(self)) is False:
            self.non_conformities.append(tr("~v section not first"))
        
        if (spec.BlankLineInSection.check(self)) is False:
            for section in self.sections_with_blank_line:
                self.non_conformities.append(tr(f"Section having blank line: {section}"))
        
        if self.sections_after_a_section:
            self.non_conformities.append(tr("Sections after ~a section"))
        
        if (spec.ValidUnitForDepth.check(self)) is False:
            self.non_conformities.append(tr(
                "If the index is depth, the units must be M (metres), F (feet) or FT (feet)"))
        
        # NEW: Special character checks
        if not spec.ValidMnemonicCharacters.check(self):
            invalid_mnemonics = spec.ValidMnemonicCharacters.get_invalid_mnemonics(self)
            for invalid in invalid_mnemonics:
                chars = ', '.join(invalid['special_chars'])
                if invalid['type'] == 'curve':
                    self.non_conformities.append(
                        tr(f"Invalid characters in mnemonic: Кривая №{invalid['index']} '{invalid['mnemonic']}' "
                           f"содержит символы: '{chars}'"))
                else:
                    self.non_conformities.append(
                        tr(f"Invalid characters in mnemonic: '{invalid['mnemonic']}' в секции {invalid['section']} "
                           f"содержит недопустимые символы: {chars}"))
        
        
        # NEW: Check for mnemonics starting with non-letter
        if not spec.MnemonicStartsWithLetter.check(self):
            invalid_start = spec.MnemonicStartsWithLetter.get_invalid_starting_mnemonics(self)
            for item in invalid_start:
                if item['type'] == 'curve':
                    self.non_conformities.append(
                        tr(f"Mnemonic does not start with letter: Кривая {item['index']} '{item['mnemonic']}' "
                           f"начинается с '{item['first_char']}'. Добавьте букву в начало."))
                else:
                    self.non_conformities.append(
                        tr(f"Mnemonic does not start with letter: '{item['mnemonic']}' в секции {item['section']} "
                           f"начинается с '{item['first_char']}'. Добавьте букву в начало."))
        
        if ('Curves' in self.sections) and (spec.DuplicateCurves.check(self)) is False:
            duplicate_curves = spec.DuplicateCurves.get_duplicate_curves_with_lines(self)
            if duplicate_curves:
                self.duplicate_curves = duplicate_curves
                duplicate_descriptions = []
                for mnemonic, line_numbers in duplicate_curves.items():
                    # Format line numbers, handling 'unknown' cases
                    line_nums_str = ', '.join(
                        str(ln) if ln != 'unknown' else '?' 
                        for ln in line_numbers
                    )
                duplicate_descriptions.append(
                    '"{}" (строки: {})'.format(mnemonic, line_nums_str)
                )
                self.non_conformities.append(
                tr("Duplicate curve mnemonics found: {}".format(', '.join(duplicate_descriptions)))
            )
        
        # Get header errors
        header_errors = self.get_all_header_errors()
        self.non_conformities.extend(header_errors)
        
        return self.non_conformities
    
    def get_all_header_errors(self):
        """Get all header errors from all sections."""
        all_header_errors = []
        for section_name, section in self.sections.items():
            if hasattr(section, 'header_errors'):
                for error in section.header_errors:
                    all_header_errors.append(tr(f"Header error in \"{section_name}\": {error}"))
        return all_header_errors
    
    def get_special_character_issues(self):
        """Get detailed information about special character issues."""
        issues = {
            'invalid_characters': [],
            'hash_characters': [],
            'invalid_start': [],
            'suggestions': []
        }
        
        # Check for invalid characters
        if not spec.ValidMnemonicCharacters.check(self):
            issues['invalid_characters'] = spec.ValidMnemonicCharacters.get_invalid_mnemonics(self)
            issues['suggestions'].append(
                "Используйте только буквы (A-Z), цифры (0-9), подчёркивание (_) и дефис (-) в мнемониках.")
        
        # Check for hash characters
        if not spec.NoHashInMnemonics.check(self):
            issues['hash_characters'] = spec.NoHashInMnemonics.get_mnemonics_with_hash(self)
            issues['suggestions'].append(
                "Замените символ # на подчёркивание (_) или удалите его. Например: 'GR#1' → 'GR_1' или 'GR1'")
        
        # Check for invalid starting characters
        if not spec.MnemonicStartsWithLetter.check(self):
            issues['invalid_start'] = spec.MnemonicStartsWithLetter.get_invalid_starting_mnemonics(self)
            issues['suggestions'].append(
                "Мнемоники должны начинаться с буквы. Например: '1CURVE' → 'C1CURVE' или 'CURVE1'")
        
        return issues
    
    def fix_special_characters(self, auto_fix=False):
        """
        Attempt to fix special character issues in mnemonics.
        
        Args:
            auto_fix (bool): If True, automatically apply fixes. If False, return suggested fixes.
        
        Returns:
            dict: Dictionary with original and suggested fixed mnemonics
        """
        fixes = {
            'curves': [],
            'well': [],
            'parameters': []
        }
        
        # Pattern for cleaning mnemonics
        special_chars_pattern = re.compile(r'[#@!$%^&*()\[\]{};:"\'<>?\\|`~+=]')
        
        # Fix curves
        if "Curves" in self.sections:
            for i, curve in enumerate(self.curves):
                original = curve.mnemonic
                fixed = special_chars_pattern.sub('_', original)
                
                # If starts with non-letter, prepend 'C'
                if fixed and not fixed[0].isalpha():
                    fixed = 'C' + fixed
                
                # Clean up multiple underscores
                fixed = re.sub(r'_+', '_', fixed)
                fixed = fixed.strip('_')
                
                if original != fixed:
                    fixes['curves'].append({
                        'index': i,
                        'original': original,
                        'fixed': fixed
                    })
                    if auto_fix:
                        curve.mnemonic = fixed
        
        # Fix well section
        if "Well" in self.sections:
            for item in self.well:
                original = item.mnemonic
                fixed = special_chars_pattern.sub('_', original)
                
                # If starts with non-letter, prepend 'W'
                if fixed and not fixed[0].isalpha():
                    fixed = 'W' + fixed
                
                # Clean up multiple underscores
                fixed = re.sub(r'_+', '_', fixed)
                fixed = fixed.strip('_')
                
                if original != fixed:
                    fixes['well'].append({
                        'original': original,
                        'fixed': fixed
                    })
                    if auto_fix:
                        item.mnemonic = fixed
        
        # Fix parameters
        if "Parameter" in self.sections:
            for item in self.params:
                original = item.mnemonic
                fixed = special_chars_pattern.sub('_', original)
                
                # If starts with non-letter, prepend 'P'
                if fixed and not fixed[0].isalpha():
                    fixed = 'P' + fixed
                
                # Clean up multiple underscores
                fixed = re.sub(r'_+', '_', fixed)
                fixed = fixed.strip('_')
                
                if original != fixed:
                    fixes['parameters'].append({
                        'original': original,
                        'fixed': fixed
                    })
                    if auto_fix:
                        item.mnemonic = fixed
        
        return fixes


class Las(LASFile):
    """LAS file object. Retained for backwards compatibility."""
    pass


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, LASFile):
            d = {"metadata": {}, "data": {}}
            for name, section in obj.sections.items():
                if isinstance(section, basestring):
                    d["metadata"][name] = section
                else:
                    d["metadata"][name] = []
                    for item in section:
                        d["metadata"][name].append(dict(item))
            for curve in obj.curves:
                d["data"][curve.mnemonic] = list(curve.data)
            return d