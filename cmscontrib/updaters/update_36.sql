begin;

create domain codename varchar
    check (value ~ '^[A-Za-z0-9_-]+$');

create domain filename varchar
    check (value ~ '^[A-Za-z0-9_.-]+$')
    check (value != '.')
    check (value != '..');

create domain filename_schema varchar
    check (value ~ '^[A-Za-z0-9_.-]+(\.%l)?$')
    check (value != '.')
    check (value != '..');

create domain filename_schema_array varchar[]
    check (array_to_string(value, '') ~ '^[A-Za-z0-9_.%-]*$')
    check (array_to_string(value, ',') ~ '^([A-Za-z0-9_.-]+(\.%l)?(,|$))*$')
    check ('.' != all(value))
    check ('..' != all(value));

create domain digest varchar
    check (value ~ '^([0-9a-f]{40}|x)$');


create function encode_filename(text varchar) returns varchar language sql immutable as $$
    select replace(text, '%', '__')
$$;

create function encode_filename_schema(text varchar) returns varchar language sql immutable as $$
    select case
        when right(text, 3) = '.%l'
            then replace(left(text, -3), '%', '__') || '.%l'
        else replace(text, '%', '__')
    end
$$;

create function encode_filename_schema_array(text varchar[]) returns varchar[] language sql immutable as $$
    select array_agg(encode_filename_schema(f))
    from unnest(text) as t(f)
$$;

update executables set filename = encode_filename(filename) where filename ~ '%';
update user_test_managers set filename = encode_filename(filename) where filename ~ '%';
update user_test_executables set filename = encode_filename(filename) where filename ~ '%';
update printjobs set filename = encode_filename(filename) where filename ~ '%';
update attachments set filename = encode_filename(filename) where filename ~ '%';
update managers set filename = encode_filename(filename) where filename ~ '%';

update files
    set filename = encode_filename_schema(filename)
    where filename != encode_filename_schema(filename);
update user_test_files
    set filename = encode_filename_schema(filename)
    where filename != encode_filename_schema(filename);

update tasks
    set submission_format = encode_filename_schema_array(submission_format)
    where submission_format != encode_filename_schema_array(submission_format);

drop function encode_filename_schema_array;
drop function encode_filename_schema;
drop function encode_filename;

rollback; -- change this to: commit;
