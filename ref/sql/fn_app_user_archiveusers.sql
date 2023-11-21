CREATE OR REPLACE FUNCTION public.app_user_archiveusers(VARIADIC p_id integer[])
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
  select array_agg(id) into v_exist_subset from public.app_user
  where id = any(p_id);
 
  -- Compare p_id with v_exist_subset and output nonexistent users
  select array_to_string(array_diff(p_id, v_exist_subset), ', ') into v_no_exist;

  -- Get users from input who are already archived
  select string_agg(id::text, ', '), count(id) into v_no_update, v_no_update_count from public.app_user
  where is_archived = true
  and id = any(p_id);
	
  -- Update app_user table
  UPDATE public.app_user
  SET is_archived = true
  WHERE id = any(p_id);
    
  -- Get number of included rows
  get diagnostics v_row_count = row_count;
 
  -- Output completion details

  -- Remind user to commit transaction
  out_msg = 'Once transaction is committed: ';
 
  -- Determine plural
  if v_row_count-v_no_update_count != 1 then
  	out_msg = concat(out_msg, v_row_count-v_no_update_count, ' users archived.');
  else
  	out_msg = concat(out_msg, v_row_count-v_no_update_count, ' user archived.');
  end if;
 
  if v_no_update != '' then
  	-- Determine plural
    if (select substring(v_no_update from ',')) is not null then
    	out_msg = concat(out_msg, ' IDs ', v_no_update, ' were already archived.');
    else
  		out_msg = concat(out_msg, ' ID ', v_no_update, ' was already archived.');
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