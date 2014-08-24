include:
  - git
  - python3
  - python3.virtualenv
  - arangodb

/home/vagrant/kimchienv:
  virtualenv.managed:
    - requirements: /vagrant/requirements.txt
    - python: /usr/bin/python3
    - runas: vagrant
    - require:
      - pkg: python3
      - pkg: python-virtualenv
      - pkg: git

install kimchi:
  cmd.run:
    - cwd: /vagrant
    - user: vagrant
    - name: "/home/vagrant/kimchienv/bin/python setup.py develop"
    - require:
      - virtualenv: /home/vagrant/kimchienv

