import pytest
from parse_abs import create_abs_dictionary

def test_create_abs_dictionary():
    # abs_dictionaryを作成
    create_abs_dictionary()
    with open("abs_dictionary.txt", "r") as f:
        lines = f.readlines()
        for line in lines:
            # 毎行最初の４つの文字列がthoremまたはdefinitionになっているかどうか、ラベルが出現した行数かどうか、absファイルかどうか、ラベル名かどうかをテストしている
            line = line.split()
            assert line[0] == "theorem" or line[0] == "definition"
            assert line[1].isdigit()
            assert ".abs" in line[2]
            assert ":" in line[3] and (line[3].split(":")[1].isdigit() or "def" in line[3].split(":")[1])
