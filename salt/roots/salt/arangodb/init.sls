/tmp/Release.key: 
  file:
    - managed
    - source: https://www.arangodb.com/repositories/arangodb2/xUbuntu_14.04/Release.key
    - source_hash: sha512=80e218f93a2ad352854cfb88a9aaa3784f858443b86e4793f5f8cf3aab7f990284900c116083c9cccedd3ab11d6b3a567f183fa96eed6ad440268004266ba5c8

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
