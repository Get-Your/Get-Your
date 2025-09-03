"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from pathlib import Path

import pytest

from merge_production_dotenvs_in_dotenv import merge


@pytest.mark.parametrize(
    ("input_contents", "expected_output"),
    [
        ([], ""),
        ([""], "\n"),
        (["JANE=doe"], "JANE=doe\n"),
        (["SEP=true", "AR=ator"], "SEP=true\nAR=ator\n"),
        (["A=0", "B=1", "C=2"], "A=0\nB=1\nC=2\n"),
        (["X=x\n", "Y=y", "Z=z\n"], "X=x\n\nY=y\nZ=z\n\n"),
    ],
)
def test_merge(
    tmp_path: Path,
    input_contents: list[str],
    expected_output: str,
):
    output_file = tmp_path / ".env"

    files_to_merge = []
    for num, input_content in enumerate(input_contents, start=1):
        merge_file = tmp_path / f".service{num}"
        merge_file.write_text(input_content)
        files_to_merge.append(merge_file)

    merge(output_file, files_to_merge)

    assert output_file.read_text() == expected_output
