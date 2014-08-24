# kimchi

Kimchi Is a Markov Chain Harangue Instigator. It's entire purpose is to reply
to a message in the hope of either funny, suprising, thought-provoking,
inspiring or just plain rude.

Although the author was a great fan of MegaHAL, he never had any intention of
writing a program of this kind. However, one day, when saying how he felt he
should write a talk for pyconuk 2014, on #python-uk on freenode, someone
challenged him to take the titles of talks at various python conferences, use
Markov Chains to generate a new title and write a talk on how he did that.

Suffice to say that the author was unable to complete the task in time to
submit a talk for pyconuk 2014. Still, there are other conferences.

## Dependencies

Kimchi requires ArangoDB to be installed - see the instructions for your sustem
at https://www.arangodb.org/download

The remaining dependencies are dealt with in the next section.

## Installing

```sh
pip install -r requirements.txt
python setup.py install
```

## Running

```sh
kimchi learn --file [learning text file]
kimchi response [a word or phrase]
```
