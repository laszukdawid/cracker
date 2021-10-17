import types
import unittest

from cracker.text_parser import TextParser


class TestTextParser(unittest.TestCase):

    sentece_24chars = "This line has 24 chars. "

    def test_paper_single_round_brackets(self):
        paper_text = "Someone said something (Smartguy, 1002)"
        expected_text = "Someone said something "
        reduced_text = TextParser.reduce_cite(paper_text)
        self.assertEqual(reduced_text, expected_text)

    def test_paper_two_round_brackets(self):
        paper_text = "It's hard to argue with this (Smartguy, 1003; Follower, 1004)"
        expected_text = "It's hard to argue with this "
        reduced_text = TextParser.reduce_cite(paper_text)
        self.assertEqual(reduced_text, expected_text)

    def test_paper_single_square_brackets(self):
        paper_text = "Someone said something [Smartguy, 1002]"
        expected_text = "Someone said something "
        reduced_text = TextParser.reduce_cite(paper_text)
        self.assertEqual(expected_text, reduced_text)

    def test_paper_two_square_brackets(self):
        paper_text = "It's hard to argue with this [Smartguy, 1003; Follower, 1004]"
        expected_text = "It's hard to argue with this "
        reduced_text = TextParser.reduce_cite(paper_text)
        self.assertEqual(reduced_text, expected_text)

    def test_split_text_generator_type(self):
        document = self.sentece_24chars

        split_text = TextParser.split_text(document)
        self.assertIsInstance(split_text, types.GeneratorType, "Return generator type")

    def test_split_text_below_3000(self):
        document = 10 * self.sentece_24chars
        self.assertEqual(len(document), 240, "Document should have 240 chars lenght")

        split_text = TextParser.split_text(document)
        list_split_text = list(split_text)
        self.assertEqual(len(list_split_text), 1, "Only one part")
        self.assertEqual(list_split_text[0], document, "First part is the document")

    def test_split_text_above_3000_below_6000(self):
        document = 200 * self.sentece_24chars
        self.assertEqual(len(document), 4800, "Document should have 4800 chars length")

        split_text = list(TextParser.split_text(document))
        self.assertEqual(len(split_text), 2, "Two parts")

    def test_split_text_above_6000(self):
        document = "no dots in this text " * 300  # 21*300 = 6300
        self.assertEqual(len(document), 6300, "Document should have 6300 chars length")

        split_text = list(TextParser.split_text(document))
        self.assertEqual(len(split_text), 3, "Two parts")
        self.assertEqual(len(split_text[0]), len(split_text[1]), "Both parts should have the same length")
        self.assertEqual(len(split_text[2]), 300, "Simple maths: 6300 - 6000 = 300")

    def test_escape_char_quote(self):
        s = 'He said "she said"'
        out_s = TextParser.escape_tags(s)
        self.assertEqual(out_s, s, "Quotes shouldn't be changed")

    def test_escape_tags_xml(self):
        s = '<he><said>She said</said></he>'
        out_s = TextParser.escape_tags(s)
        expected_s = '&lt;he&gt;&lt;said&gt;She said&lt;/said&gt;&lt;/he&gt;'
        self.assertEqual(out_s, expected_s, "Tags should be converted to &...;")
