-- Get-Your is a platform for application and administration of income-
-- qualified programs, used primarily by the City of Fort Collins.
-- Copyright (C) 2023

-- This program is free software: you can redistribute it and/or modify
-- it under the terms of the GNU General Public License as published by
-- the Free Software Foundation, either version 3 of the License, or
-- (at your option) any later version.

-- This program is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU General Public License for more details.

-- You should have received a copy of the GNU General Public License
-- along with this program.  If not, see <https://www.gnu.org/licenses/>.
create or replace function array_diff(test_array anyarray, compare_array anyarray)
returns anyarray language sql immutable as $$
    select coalesce(array_agg(elem), '{}')
    from unnest(test_array) elem
    where elem <> all(compare_array)
$$;