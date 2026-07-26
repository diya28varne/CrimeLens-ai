"""Locale helpers for CrimeLens API — English / Kannada content (no machine-page translate)."""

from __future__ import annotations

from typing import Literal

Locale = Literal["en", "kn"]

# Structured UI/AI strings used by Advisor, Reports, Explain disclaimers.
STRINGS: dict[str, dict[Locale, str]] = {
    "disclaimer_reports": {
        "en": (
            "Intelligence report assembled from CrimeLens analytics, predictions, and explanations. "
            "Observed = measured incidents; Forecast = model estimates. Not an operational order."
        ),
        "kn": (
            "ಕ್ರೈಮ್‌ಲೆನ್ಸ್ ವಿಶ್ಲೇಷಣೆ, ಭವಿಷ್ಯವಾಣಿ ಮತ್ತು ವಿವರಣೆಗಳಿಂದ ಜೋಡಿಸಲಾದ ಬುದ್ಧಿವಂತಿಕೆ ವರದಿ. "
            "ಗಮನಿಸಿದ = ಅಳತೆ ಮಾಡಿದ ಘಟನೆಗಳು; ಭವಿಷ್ಯವಾಣಿ = ಮಾದರಿ ಅಂದಾಜು. ಕಾರ್ಯಾಚರಣಾ ಆದೇಶವಲ್ಲ."
        ),
    },
    "disclaimer_advisor": {
        "en": (
            "Intelligence briefing grounded in CrimeLens analytics, predictions, and network data. "
            "Observed = measured from incidents; Forecast = model estimates. Not operational orders."
        ),
        "kn": (
            "ಕ್ರೈಮ್‌ಲೆನ್ಸ್ ವಿಶ್ಲೇಷಣೆ, ಭವಿಷ್ಯವಾಣಿ ಮತ್ತು ಜಾಲ ಡೇಟಾದಲ್ಲಿ ಆಧಾರಿತ ಬುದ್ಧಿವಂತಿಕೆ ಬ್ರೀಫಿಂಗ್. "
            "ಗಮನಿಸಿದ = ಘಟನೆಗಳಿಂದ ಅಳತೆ; ಭವಿಷ್ಯವಾಣಿ = ಮಾದರಿ ಅಂದಾಜು. ಕಾರ್ಯಾಚರಣಾ ಆದೇಶಗಳಲ್ಲ."
        ),
    },
    "disclaimer_explain": {
        "en": (
            "Explainable decision support grounded in model contributions and platform data. "
            "Factors are model estimates — not proof of causation. Humans retain operational authority."
        ),
        "kn": (
            "ಮಾದರಿ ಕೊಡುಗೆಗಳು ಮತ್ತು ಪ್ಲಾಟ್‌ಫಾರ್ಮ್ ಡೇಟಾದಲ್ಲಿ ಆಧಾರಿತ ವಿವರಣಾತ್ಮಕ ನಿರ್ಧಾರ ಬೆಂಬಲ. "
            "ಅಂಶಗಳು ಮಾದರಿ ಅಂದಾಜು — ಕಾರಣತ್ವದ ಪುರಾವೆಯಲ್ಲ. ಮಾನವರೇ ಕಾರ್ಯಾಚರಣಾ ಅಧಿಕಾರ ಹೊಂದಿರುತ್ತಾರೆ."
        ),
    },
    "report_subtitle": {
        "en": "AI-Powered Crime Intelligence Report",
        "kn": "ಕೃತಕ ಬುದ್ಧಿಮತ್ತೆ ಆಧಾರಿತ ಅಪರಾಧ ಬುದ್ಧಿವಂತಿಕೆ ವರದಿ",
    },
    "prepared_for": {
        "en": "Karnataka State Police Command",
        "kn": "ಕರ್ನಾಟಕ ರಾಜ್ಯ ಪೊಲೀಸ್ ಕಮಾಂಡ್",
    },
    "classification": {
        "en": "Official Use Only",
        "kn": "ಅಧಿಕೃತ ಬಳಕೆ ಮಾತ್ರ",
    },
    "section_cover": {"en": "Cover", "kn": "ಮುಖಪುಟ"},
    "section_exec": {"en": "Executive Summary", "kn": "ಕಾರ್ಯನಿರ್ವಾಹಕ ಸಾರಾಂಶ"},
    "section_overview": {"en": "Crime Overview", "kn": "ಅಪರಾಧ ಅವಲೋಕನ"},
    "section_hotspot": {"en": "Hotspot Analysis", "kn": "ಹಾಟ್‌ಸ್ಪಾಟ್ ವಿಶ್ಲೇಷಣೆ"},
    "section_pred": {"en": "Predictions", "kn": "ಭವಿಷ್ಯವಾಣಿಗಳು"},
    "section_rec": {"en": "Operational Recommendations", "kn": "ಕಾರ್ಯಾಚರಣಾ ಶಿಫಾರಸುಗಳು"},
    "section_check": {"en": "Action Checklist", "kn": "ಕ್ರಮ ಪರಿಶೀಲನಾ ಪಟ್ಟಿ"},
    "action_increase_patrol": {
        "en": "Increase Patrol",
        "kn": "ಗಸ್ತು ಹೆಚ್ಚಿಸಿ",
    },
    "action_deploy_cctv": {"en": "Deploy CCTV", "kn": "ಸಿಸಿಟಿವಿ ನಿಯೋಜಿಸಿ"},
    "action_deploy_drone": {"en": "Deploy Drone", "kn": "ಡ್ರೋನ್ ನಿಯೋಜಿಸಿ"},
    "action_traffic": {"en": "Traffic Diversion", "kn": "ಸಂಚಾರ ವಾಹನ ಮಾರ್ಗ ಬದಲಾವಣೆ"},
    "action_community": {"en": "Community Awareness", "kn": "ಸಮುದಾಯ ಜಾಗೃತಿ"},
    "action_emergency": {"en": "Emergency Response", "kn": "ತುರ್ತು ಪ್ರತಿಕ್ರಿಯೆ"},
    "action_investigation": {"en": "Investigation Priority", "kn": "ತನಿಖಾ ಆದ್ಯತೆ"},
    "action_none": {"en": "No Action", "kn": "ಯಾವುದೇ ಕ್ರಮವಿಲ್ಲ"},
    "template_daily": {
        "en": "Daily Intelligence Brief",
        "kn": "ದೈನಂದಿನ ಬುದ್ಧಿವಂತಿಕೆ ಬ್ರೀಫ್",
    },
    "template_weekly": {
        "en": "Weekly Crime Analysis",
        "kn": "ಸಾಪ್ತಾಹಿಕ ಅಪರಾಧ ವಿಶ್ಲೇಷಣೆ",
    },
    "template_festival": {
        "en": "Festival Security Assessment",
        "kn": "ಹಬ್ಬದ ಭದ್ರತಾ ಮೌಲ್ಯಮಾಪನ",
    },
    "exec_summary_prefix": {
        "en": "Executive outlook:",
        "kn": "ಕಾರ್ಯನಿರ್ವಾಹಕ ನೋಟ:",
    },
    "risk_high": {"en": "High", "kn": "ಅಧಿಕ"},
    "risk_medium": {"en": "Medium", "kn": "ಮಧ್ಯಮ"},
    "risk_low": {"en": "Low", "kn": "ಕಡಿಮೆ"},
    "risk_critical": {"en": "Critical", "kn": "ಗಂಭೀರ"},
}


def normalize_locale(value: str | None) -> Locale:
    if not value:
        return "en"
    v = value.strip().lower()
    if v.startswith("kn"):
        return "kn"
    return "en"


def locale_from_header(accept_language: str | None, x_locale: str | None = None) -> Locale:
    if x_locale:
        return normalize_locale(x_locale)
    if not accept_language:
        return "en"
    primary = accept_language.split(",")[0].strip()
    return normalize_locale(primary)


def t(key: str, locale: Locale = "en") -> str:
    entry = STRINGS.get(key)
    if not entry:
        return key
    return entry.get(locale) or entry.get("en") or key


def translate_action_title(title: str, locale: Locale) -> str:
    mapping = {
        "Increase Patrol": "action_increase_patrol",
        "Deploy CCTV": "action_deploy_cctv",
        "Deploy Drone": "action_deploy_drone",
        "Traffic Diversion": "action_traffic",
        "Community Awareness": "action_community",
        "Emergency Response": "action_emergency",
        "Investigation Priority": "action_investigation",
        "No Action": "action_none",
    }
    key = mapping.get(title)
    return t(key, locale) if key else title
