import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
name="sylfenUtils",
version="1.1",
author="Dorian Drevon",
author_email="drevondorian@gmail.com",
description="Utilities package",
long_description=long_description,
long_description_content_type="text/markdown",
classifiers=[
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
],
packages=setuptools.find_packages(),
package_data={'': ['conf/*',
        'static/lib/*','static/lib/js/*','static/lib/css/*','static/lib/pictures/*',
        'templates/*']},
include_package_data=True,
install_requires=['IPython','pandas==1.3.1','psycopg2-binary','odfpy==1.4.1','plotly>=5.5.0',
    'pymodbus==2.5.3','opcua==0.98.13','cryptography==2.8','Pillow==7.0.0','openpyxl==3.0.7',
    'psutil==5.8.0','colorama==0.4.3','Flask==2.2.2','scipy']
,python_requires=">=3.8"
)
