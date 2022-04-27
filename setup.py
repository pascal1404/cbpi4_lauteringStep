from setuptools import setup

setup(name='cbpi4_lauteringStep',
      version='0.0.4',
      description='CraftBeerPi Plugin Lautering Step',
      author='Pascal Scholz',
      author_email='pascal1404@gmx.de',
      url='https://github.com/pascal1404/cbpi4_lauteringStep',
      include_package_data=True,
      package_data={
        # If any package contains *.txt or *.rst files, include them:
      '': ['*.txt', '*.rst', '*.yaml'],
      'cbpi4_lauteringStep': ['*','*.txt', '*.rst', '*.yaml']},
      packages=['cbpi4_lauteringStep'],
     )