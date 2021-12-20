import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
dirParent = "dorianUtils"

setuptools.setup(
name="dorianUtilsModulaire", # Replace with your own username
version="3.13.1",
author="Dorian Drevon",
author_email="drevondorian@gmail.com",
description="Utilities package",
long_description=long_description,
long_description_content_type="text/markdown",
# url="https://github.com/pypa/sampleproject",
# project_urls={
#     "Bug Tracker": "https://github.com/pypa/sampleproject/issues",
# },
classifiers=[
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
],
# package_dir={"": dirParent},
# packages=['dorianUtils'],
packages=setuptools.find_packages(),
package_data={'': ['conf/*']},
include_package_data=True,
install_requires=['IPython','matplotlib','scipy','pandas==1.3.1',
                    'dash==1.20.0','dash-daq==0.5.0','dash_bootstrap_components==0.13.0','flask_caching','psycopg2-binary',
                    'pyModbusTCP==0.1.10','opcua==0.98.9','cryptography==2.8'],
python_requires=">=3.8"
)
