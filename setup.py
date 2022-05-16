from setuptools import PackageFinder, setup, find_packages

setup(
    name='abquant',
    version='1.1.4',
    description='event-driven quant dev tools',
    author='independent regime',
    # package_dir={"":"./abquant"},
    # packages=find_packages(where='abquant'),
    packages=find_packages(where='./'),
    package_data={
        'abquantui': ['logging_template.yaml']
    },
    install_requires=[
        'numpy',
        'requests',
        'websocket-client',
        'pytz',
        'ecdsa',
        'pandas',
        'telegram',
    ],
    python_requires='>=3.8',

)
