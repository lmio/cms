begin;

create function encode_codename(text varchar, allow varchar) returns varchar language sql immutable as $$
    select
        string_agg(
            case
                when c ~* allow
                    then c
                else '__' || to_hex(ascii(c))
            end,
            ''
        )
    from unnest(regexp_split_to_array(text, '')) as s(c)
$$;


update admins
    set username = encode_codename(username, '[a-z0-9_-]')
    where username !~* '^[a-z0-9_-]*$';
update contests
    set name = encode_codename(name, '[a-z0-9_-]')
    where name !~* '^[a-z0-9_-]*$';
update tasks
    set name = encode_codename(name, '[a-z0-9_-]')
    where name !~* '^[a-z0-9_-]*$';
update testcases
    set codename = encode_codename(codename, '[a-z0-9_-]')
    where codename !~* '^[a-z0-9_-]*$';
update users
    set username = encode_codename(username, '[a-z0-9_-]')
    where username !~* '^[a-z0-9_-]*$';
update teams
    set code = encode_codename(code, '[a-z0-9_-]')
    where code !~* '^[a-z0-9_-]*$';

update printjobs
    set filename = encode_codename(filename, '[a-z0-9_%.-]')
    where filename !~* '^[a-z0-9_%.-]*$';
update files
    set filename = encode_codename(filename, '[a-z0-9_%.-]')
    where filename !~* '^[a-z0-9_%.-]*$';
update executables
    set filename = encode_codename(filename, '[a-z0-9_%.-]')
    where filename !~* '^[a-z0-9_%.-]*$';
update attachments
    set filename = encode_codename(filename, '[a-z0-9_%.-]')
    where filename !~* '^[a-z0-9_%.-]*$';
update submission_format_elements
    set filename = encode_codename(filename, '[a-z0-9_%.-]')
    where filename !~* '^[a-z0-9_%.-]*$';
update managers
    set filename = encode_codename(filename, '[a-z0-9_%.-]')
    where filename !~* '^[a-z0-9_%.-]*$';
update user_test_files
    set filename = encode_codename(filename, '[a-z0-9_%.-]')
    where filename !~* '^[a-z0-9_%.-]*$';
update user_test_managers
    set filename = encode_codename(filename, '[a-z0-9_%.-]')
    where filename !~* '^[a-z0-9_%.-]*$';
update user_test_executables
    set filename = encode_codename(filename, '[a-z0-9_%.-]')
    where filename !~* '^[a-z0-9_%.-]*$';

drop function encode_codename;

alter table participations
    alter ip type cidr[] using string_to_array(ip, ',')::cidr[];

rollback; -- change this to: commit;
