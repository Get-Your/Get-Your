create or replace function array_diff(test_array anyarray, compare_array anyarray)
returns anyarray language sql immutable as $$
    select coalesce(array_agg(elem), '{}')
    from unnest(test_array) elem
    where elem <> all(compare_array)
$$;