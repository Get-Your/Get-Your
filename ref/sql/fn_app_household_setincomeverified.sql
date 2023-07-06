CREATE OR REPLACE FUNCTION public.app_household_setincomeverified(VARIADIC p_id integer[])
 RETURNS character varying
 LANGUAGE plpgsql
AS $$
declare
  v_exist_subset integer[] default array[]::integer[];
  v_no_exist varchar(1000) default '';
  v_no_update varchar(1000) default '';
  v_row_count integer DEFAULT 0;
  v_no_update_count integer DEFAULT 0;
  out_msg varchar(1000) default '';
begin

  -- Get users from input that aren't in the target table
  select array_agg(user_id) into v_exist_subset from public.app_household
  where user_id = any(p_id);
 
  -- Compare p_id with v_exist_subset and output nonexistent users
  select array_to_string(array_diff(p_id, v_exist_subset), ', ') into v_no_exist;

  -- Get users from input who are already income-verified
  select string_agg(user_id::text, ', '), count(user_id) into v_no_update, v_no_update_count from public.app_household
  where is_income_verified = true
  and user_id = any(p_id);
	
  -- Update app_household table
  UPDATE public.app_household
  SET is_income_verified = true
  WHERE user_id = any(p_id);
    
  -- Get number of included rows
  get diagnostics v_row_count = row_count;
 
  -- Output completion details
 
  -- Determine plural
  if v_row_count-v_no_update_count != 1 then
  	out_msg = concat(v_row_count-v_no_update_count, ' users verified.');
  else
  	out_msg = concat(v_row_count-v_no_update_count, ' user verified.');
  end if;
 
  if v_no_update != '' then
  	-- Determine plural
    if (select substring(v_no_update from ',')) is not null then
    	out_msg = concat(out_msg, ' IDs ', v_no_update, ' were already verified.');
    else
  		out_msg = concat(out_msg, ' ID ', v_no_update, ' was already verified.');
    end if;
  end if;
  
  if v_no_exist != '' then
  	-- Determine plural
  	if (select substring(v_no_exist from ',')) is not null then
  		out_msg = concat(out_msg, ' IDs ', v_no_exist, ' don''t exist.');
  	else
  		out_msg = concat(out_msg, ' ID ', v_no_exist, ' doesn''t exist.');
  	end if;
  end if;
  
  return out_msg;
END
$$
;