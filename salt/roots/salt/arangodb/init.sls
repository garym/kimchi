/tmp/Release.key: 
  file:
    - managed
    - source: https://www.arangodb.org/repositories/arangodb2/xUbuntu_14.04/Release.key
    - source_hash: sha512=0e78f8dd3dcec395a2ba27e4f5483b9c4621b0fd8d59961aa5611519d5d6c6bb8ddd7c42d824931030c02be77205a7ff84e83ba487c48df7525def6c64517569

add_arango_key:
  cmd.run:
    - name: apt-key add - < /tmp/Release.key
    - user: root
    - require:
      - file: /tmp/Release.key

/etc/apt/sources.list.d/arangodb.list:
  file:
    - managed
    - source: salt://arangodb/apt_sources.list
    - template: jinja
    - mode: 644

apt-get update:
  cmd.run:
    - user: root
    - require:
      - file: /etc/apt/sources.list.d/arangodb.list
      - cmd: add_arango_key

arangodb:
  pkg:
    - installed
    - require:
      - cmd: apt-get update
