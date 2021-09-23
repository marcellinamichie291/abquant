from setuptools import PackageFinder, setup, find_packages

setup(
    name='abquant',
    version='0.2.0',
    description='event-driven quant dev tools',
    author='independent regime',
    # package_dir={"":"./abquant"},
    # packages=find_packages(where='abquant'),
    packages=find_packages(where='./'),
    install_requires=[
        'numpy',
        'requests',
        'websocket-client',
        'pytz',

    ],
    python_requires='>=3.8',

)
