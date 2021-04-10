
from setuptools import setup, find_namespace_packages

setup(
    name='sparky-screen_fast-api-server',
    version='0.0.0',
    description='Code for running igus cnc machine',
    author='Bruce Wilcoxon',
    author_email='bruce.wilcoxon@wsrobots.com',
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src"),
    install_requires=[
        'fastapi',
        'starlette',
        'uvicorn[standard]',
        'aiofiles',
        'watchdog',
        'gpiozero'
    ]
)
