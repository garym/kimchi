# KIMCHI

KIMCHI Is a Markov Chain Harangue Instigator. It's entire purpose is to reply
to a message in the hope of getting either funny, suprising, thought-provoking,
inspiring or just plain rude responses.

Although the author was a great fan of MegaHAL, he never had any intention of
writing a program of this kind. However, one day, when saying how he felt he
should write a talk for pyconuk 2014, on #python-uk on freenode, someone
challenged him to take the titles of talks at various python conferences, use
Markov Chains to generate a new title and write a talk on how he did that.

Suffice to say that the author was unable to complete the task in time to
submit a talk for pyconuk 2014. Still, there are other conferences.


## Dependencies

Kimchi requires ArangoDB to be installed - see the instructions for your system
at https://www.arangodb.org/download

Kimchi also makes use of PyStemmer which, if installed from source, needs to be
compiled. This requires the Python 3 development libraries and compiler tools.
It may also be possible to install PyStemmer directly from your distribution
repositories.

For the former approach:

 * On Debian/Ubuntu:


   ```sh
   sudo apt-get install python3-dev build-essential
   ```

 * On Fedora (untested):

   ```sh
   sudo yum install python-devel
   ```

The remaining dependencies, including actually installing PyStemmer are dealt
with in the next section.

## Installing

```sh
pip install -r requirements.txt
python setup.py install
```

## Running

```sh
kimchi learn [learning text file]
kimchi reply "a word or phrase" ["another word or phrase" [...]]
```

Optionally you can specify a database in order to separate out specific
personalities:

```sh
kimchi learn --dbname=aliens < aliens.trn
kimchi reply --dbname=aliens "where are the aliens?"
```

which, depending on the text in aliens.trn and luck, might respond with:

```
Aliens? You mean the air ducts?
```

## Learning files

While it is possible to teach kimchi to talk from scratch, this could be a very slow process and so it is expected that you will load in data from a file.

An example learning file might look something like this:

```
# This is a comment
Hello, how are you?
My name is Kim.
Who are you?
# And so on
```

A # at the beginning of a line will result in it being ignored.

Kimchi does not currently provide any sample data but it should be compatible
with .trn files for MegaHAL (see http://megahal.sourceforge.net/download/old
for zip files for examples).

Note that if your data source is a plain text log file, it is relatively easy
to process such a log file with sed to clean up the data. For example, for
hexchat's irc logs, you could get a reasonably good sample of the data with
the following command:

```sh
sed -e '/\*/ d' \
    -e 's/^.*\t//' \
    path/to/logfile.log  > logfile.trn
```

which removes any line with an asterisk (which might be overkill) and strips
the beginning of lines up to the last tab.

If in addition you use an irc bouncer, you might need to do some additional
cleanup. For example, for bip you might do this:

```sh
sed -e '/End of backlog/ d' \
    -e '/\*/ d' \
    -e 's/^.*\t//' \
    -e 's/^[0-9][^>].*>//' \
    path/to/logfile.log > logfile.trn
```

which additionally strips the "End of backlog" message and attempts to remove the timestamp at the beginning of lines repeated from the backlog.
