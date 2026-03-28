"""
Exercise analyzer registry.
Each analyzer takes (landmarks, w, h, state) and mutates state in-place.
To add a new exercise: create its module here and add it to ANALYZERS.
"""
from .pushups        import analyze_pushups
from .squats         import analyze_squats
from .bicep_curls    import analyze_bicep_curls
from .shoulder_press import analyze_shoulder_press

ANALYZERS = {
    "pushups":        analyze_pushups,
    "squats":         analyze_squats,
    "bicep_curls":    analyze_bicep_curls,
    "shoulder_press": analyze_shoulder_press,
}
