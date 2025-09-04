from __future__ import print_function

# Standard library packages
import json
import logging
import re

try:
    unicode = unicode
except NameError:
    unicode = str
    basestring = (str, bytes)
else:
    bytes = str

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
}

def tr(msg):
    for eng, rus in ERROR_MESSAGES.items():
        if msg.startswith(eng):
            return msg.replace(eng, rus)
    return ERROR_MESSAGES.get(msg, msg)


class LASFile(object):
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

    def read(self, file_ref, ignore_data=False, read_policy="default", null_policy="strict", ignore_header_errors=False, mnemonic_case="upper", index_unit=None, **kwargs):
        file_obj, self.encoding = reader.open_file(file_ref, **kwargs)
        regexp_subs, value_null_subs, version_NULL = reader.get_substitutions(read_policy, null_policy)
        try:
            self.raw_sections, self.sections_after_a_section, self.v_section_first, self.blank_line_in_section, self.sections_with_blank_line = reader.read_file_contents(file_obj, regexp_subs, value_null_subs, ignore_data=ignore_data)
        finally:
            if hasattr(file_obj, "close"):
                file_obj.close()

        if len(self.raw_sections) == 0:
            raise KeyError(tr("No ~ sections found. Is this a LAS file?"))

        def add_section(pattern, name, **sect_kws):
            raw_section = self.match_raw_section(pattern)
            drop = []
            if raw_section:
                self.sections[name] = reader.parse_header_section(raw_section, **sect_kws)
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

        add_section("~V", "Version", version=1.2, ignore_header_errors=ignore_header_errors, mnemonic_case=mnemonic_case)

        if self.match_raw_section("~V"):
            self.duplicate_v_section = True
            self.non_conformities.append(tr("Duplicate v section"))

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

        try:
            assert version in (1.2, 2, None)
        except AssertionError:
            version = 1.2 if version < 2 else 2
        else:
            if version is None:
                logger.info(tr("Assuming that LAS VERS is 2.0"))
                version = 2

        add_section("~W", "Well", version=version, ignore_header_errors=ignore_header_errors, mnemonic_case=mnemonic_case)

        if self.match_raw_section("~W"):
            self.duplicate_w_section = True
            self.non_conformities.append(tr("Duplicate w section"))

        try:
            null = self.well["NULL"].value
        except KeyError:
            logger.warning(tr("NULL item not found in the ~W section"))
            null = None

        add_section("~C", "Curves", version=version, ignore_header_errors=ignore_header_errors, mnemonic_case=mnemonic_case)

        if self.match_raw_section("~C"):
            self.duplicate_c_section = True
            self.non_conformities.append(tr("Duplicate c section"))

        add_section("~P", "Parameter", version=version, ignore_header_errors=ignore_header_errors, mnemonic_case=mnemonic_case)

        if self.match_raw_section("~P"):
            self.duplicate_p_section = True
            self.non_conformities.append(tr("Duplicate p section"))

        add_special_section("~A", "Ascii")
        add_special_section("~O", "Other")
        if self.match_raw_section("~O"):
            self.duplicate_o_section = True
            self.non_conformities.append(tr("Duplicate o section"))

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
            if "Curves" in self.sections and len(self.curves) > 0:
                check_units_on.append(self.curves[0])
            for index_unit, possibilities in defaults.DEPTH_UNITS.items():
                if all(i.unit.upper() in possibilities for i in check_units_on):
                    self.index_unit = index_unit

    # Остальной код класса остаётся прежним, только в местах ошибок и предупреждений используется tr()
