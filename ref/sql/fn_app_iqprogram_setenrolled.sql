CREATE OR REPLACE FUNCTION public.app_iqprogram_setenrolled(programname varchar(40), VARIADIC p_id integer[])
 RETURNS character varying
 LANGUAGE plpgsql
AS $$
declare
  programid integer default 0;
  v_exist_subset integer[] default array[]::integer[];
  v_no_exist varchar(1000) default '';
  v_no_update varchar(1000) default '';
  v_row_count integer DEFAULT 0;
  out_msg varchar(1000) default '';
begin
	
  -- Get the program_id for use in the rest of the script
  select id into programid from public.app_iqprogramrd 
  where is_active = true 
  and program_name = programname;
 
  -- Ensure the program exists
  if programid is null then
  	out_msg = 'The specified program is not an active program.';
  	
  else

    -- Get users from input that aren't in the target table
    select array_agg(user_id) into v_exist_subset from public.app_iqprogram
    where program_id = programid 
    and user_id = any(p_id);
   
    -- Compare p_id with v_exist_subset and output nonexistent users
    select array_to_string(array_diff(p_id, v_exist_subset), ', ') into v_no_exist;
  
    -- Get users from input who are already enrolled
    select string_agg(user_id::text, ', ') into v_no_update from public.app_iqprogram
    where program_id = programid 
    and is_enrolled = true
    and user_id = any(p_id);
  	
    -- Update app_iqprogram table, but only if is_enrolled is false (for timestamp validity)
    UPDATE public.app_iqprogram
    SET is_enrolled = true, enrolled_at = now()
    WHERE program_id = programid 
    and is_enrolled = false
    and user_id = any(p_id);
   
    -- Get number of included rows
    get diagnostics v_row_count = row_count;
   
    -- Output completion details
   
    -- Determine plural
    if v_row_count != 1 then
    	out_msg = concat(v_row_count, ' users enrolled.');
    else
    	out_msg = concat(v_row_count, ' user enrolled.');
    end if;
   
    if v_no_update != '' then
    	-- Determine plural
      if (select substring(v_no_update from ',')) is not null then
      	out_msg = concat(out_msg, ' IDs ', v_no_update, ' were already enrolled.');
      else
    		out_msg = concat(out_msg, ' ID ', v_no_update, ' was already enrolled.');
      end if;
    end if;
    
    if v_no_exist != '' then
    	-- Determine plural
    	if (select substring(v_no_exist from ',')) is not null then
    		out_msg = concat(out_msg, ' IDs ', v_no_exist, ' don''t exist for this program.');
    	else
    		out_msg = concat(out_msg, ' ID ', v_no_exist, ' doesn''t exist for this program.');
    	end if;
    end if;
   
  end if;
  
  return out_msg;
END
$$
;