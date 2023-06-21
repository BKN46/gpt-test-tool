from typing import List


def read_srt(lines: List[str]) -> List[str]:
    res = []
    tmp = []
    combine_next = False
    for line in lines:
        if line.strip() == "" and tmp:
            if not tmp[0].isdigit():
                tmp = [int(res[-1][0]) + 1] + tmp
            res.append(tmp)
            tmp = []
        elif line.strip() != "":
            if combine_next:
                tmp[-1] += " " + line.strip()
                combine_next = False
            elif line.strip()[-1].isalpha() and line.strip()[-1].islower:
                tmp.append(line.strip())
                combine_next = True
            else:
                tmp.append(line.strip())
        combine_next = False
    return res
