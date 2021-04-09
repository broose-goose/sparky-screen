from setuptools import setup, find_namespace_packages

setup(
    name='covid_edge_system_igus',
    version='0.0.0',
    description='Code for running igus cnc machine',
    author='Bruce Wilcoxon',
    author_email='bruce.wilcoxon@wsrobots.com',
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src"),
    install_requires=[
        'kivy[full]',
        'watchdog',
        'gpiozero',
        'screeninfo'
    ]
)
