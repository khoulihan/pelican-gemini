
from pelican import signals
from pelican.readers import BaseReader


class GeminiReader(BaseReader):
    enabled = True

    file_extensions = ['gmi', 'gemini']

    def read(self, filename):
        metadata = {}
        content = ""
        with open(filename, mode='r') as f:
            end_of_meta = False
            while not end_of_meta:
                current = f.readline()
                if current == '\n' or current == '':
                    end_of_meta = True
                    continue
                current = current.strip()
                split = current.split(': ')
                metadata[split[0].lower()] = split[1]
            # After the first blank line, the rest is content.
            content = f.read()

        parsed = {}
        for key, value in metadata.items():
            parsed[key] = self.process_metadata(key, value)

        return content, parsed


def add_reader(readers):
    for ext in GeminiReader.file_extensions:
        readers.reader_classes[ext] = GeminiReader


def register():
    signals.readers_init.connect(add_reader)
