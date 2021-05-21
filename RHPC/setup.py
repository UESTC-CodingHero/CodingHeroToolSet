from setuptools import setup, find_packages

setup(name="hpc",
      version="1.0",
      license="GPLv2",
      description="The package is used for HPC management, it encapsulates some commands of HPC",
      keywords=["hpc", "job"],
      author="Xueli Cheng",
      author_email="xueli.cheng@qq.com",
      packages=find_packages(),
      include_package_data=True
      )
