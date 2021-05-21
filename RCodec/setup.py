from setuptools import setup, find_packages

setup(name="codec",
      version="2.0",
      license="GPLv2",
      description="The package is used for executing codec job in HPC cluster or local machine",
      keywords=["hpc", "codec"],
      author="Xueli Cheng",
      author_email="xueli.cheng@qq.com",
      packages=find_packages(),
      include_package_data=True,
      package_data={"": ["*.xlsm", "*.json"]},
      )
