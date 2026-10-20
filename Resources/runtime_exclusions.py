"""Unused legacy dependencies for the pinned AniCanto inference paths.

This does not change upstream package licences. Do not apply this policy to an
arbitrary Python environment or to Demucs/quantization training workflows.
"""
EXCLUDED={
    'separator-runtime':('diffq','diffq-fixed'),
    'analysis':('diffq','diffq-fixed'),
    'gsv-runtime':('distance',),
    'gpt':('distance',),
}

def cleanup_command(root,python,name,packages):
    names=[key for key in EXCLUDED.get(name,()) if key in packages]
    from runtime_installer import pip_command
    return pip_command(python,root,'uninstall','-y',*names) if names else None
