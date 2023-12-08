import setuptools,re

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

base_version=re.search('(ScadaUtils V)(\d+\.\d*)',long_description).groups()[1]
v_try='4'

setuptools.setup(
    name="scadaUtils",
    version=base_version+'.'+v_try,
    author="Dorian Drevon",
    author_email="drevondorian@gmail.com",
    description="Utilities package",
    url='https://github.com/dorian2science/scadaUtils',
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    package_data={'': ['conf/*',
            'static/*','static/js/*','static/css/*','static/html/*','static/tmp/',
            'templates/*','rsoc_units.txt']},
    include_package_data=True,
    install_requires=['IPython','pandas>=1.5.2','psycopg2-binary','odfpy==1.4.1','plotly>=5.5.0',
        'pymodbus==2.5.3','opcua==0.98.13','cryptography==2.8','Pillow','openpyxl==3.0.7',
        'psutil>=5.8.0','colorama==0.4.3','Flask>=2.2.2','scipy','pyads','gunicorn',
        'coolprop>=6.4.3.post1','pint>=0.20.1',
        'Flask-WTF', 'Flask-Login','Flask-SQLAlchemy','Flask-Migrate',
        ]
    ,python_requires=">=3.8"
)
