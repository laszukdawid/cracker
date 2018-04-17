import unittest

from aws_polly_gui.text_parser import TextParser


class TestTextParser(unittest.TestCase):
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

