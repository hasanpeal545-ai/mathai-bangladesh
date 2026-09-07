# Per-class SSC board style rules
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class ClassStandard:
    class_range: str
    complexity: str
    style_description: str
    required_markers: List[str] = field(default_factory=list)
    notation: str = "informal"


CLASS_6_7 = ClassStandard(
    class_range="6-7",
    complexity="simple",
    style_description=(
        "সহজ বাংলায় ব্যাখ্যা করবে, ছোট ছোট ধাপে ভাগ করে দেখাবে, "
        "বেশি উদাহরণ দেবে। Notation informal কিন্তু গাণিতিকভাবে সঠিক হতে হবে।"
    ),
    notation="informal",
)

CLASS_8 = ClassStandard(
    class_range="8",
    complexity="medium",
    style_description=(
        "মাঝারি জটিলতায় ব্যাখ্যা করবে এবং প্রাসঙ্গিক সূত্র (formula) "
        "পরিচয় করিয়ে দেবে।"
    ),
    notation="semi-formal",
)

CLASS_9_10 = ClassStandard(
    class_range="9-10",
    complexity="exact_ssc",
    style_description=(
        "SSC Board এর ঠিক ফরম্যাট অনুসরণ করবে — 'সমাধানঃ' দিয়ে শুরু হবে, "
        "'দেওয়া আছে,', 'আমরা জানি,', 'সূত্রমতে,' লেখা হবে, '∴' চিহ্ন ব্যবহার হবে, "
        "এবং শেষে '(উত্তর)' দিয়ে শেষ হবে।"
    ),
    required_markers=["সমাধানঃ", "দেওয়া আছে,", "আমরা জানি,", "সূত্রমতে,", "∴", "(উত্তর)"],
    notation="formal_ssc",
)


def get_class_standard(class_number: int) -> ClassStandard:
    if not 6 <= class_number <= 10:
        raise ValueError("class_number must be between 6 and 10")
    if class_number in (6, 7):
        return CLASS_6_7
    if class_number == 8:
        return CLASS_8
    return CLASS_9_10
