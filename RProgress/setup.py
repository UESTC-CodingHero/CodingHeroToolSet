from setuptools import setup, find_packages

setup(name="hpc_progress",
      version="1.0",
      license="GPLv2",
      description="The package is used for HPC progress management",
      keywords=["hpc", "progress"],
      author="Xueli Cheng",
      author_email="xueli.cheng@qq.com",
      packages=find_packages(),
      include_package_data=True,
      entry_points={'console_scripts': [
          'progress_server = progress.app_master:main',
      ]},
      )
