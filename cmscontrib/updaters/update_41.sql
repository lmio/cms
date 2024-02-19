begin;

alter domain filename_schema
    drop constraint filename_schema_check;
alter domain filename_schema
    drop constraint filename_schema_check1;
alter domain filename_schema
    drop constraint filename_schema_check2;
alter domain filename_schema
    add constraint filename_schema_check check (VALUE ~ '^[A-Za-z0-9_.-]+(.%l)?$');
alter domain filename_schema
	add constraint filename_schema_check1 check (VALUE != '.');
alter domain filename_schema
	add constraint filename_schema_check2 check (VALUE != '..');

alter domain filename_schema_array
    drop constraint filename_schema_array_check;
alter domain filename_schema_array
    drop constraint filename_schema_array_check1;
alter domain filename_schema_array
    drop constraint filename_schema_array_check2;
alter domain filename_schema_array
    drop constraint filename_schema_array_check3;
alter domain filename_schema_array
	add constraint filename_schema_array_check check (array_to_string(VALUE, '') ~ '^[A-Za-z0-9_.%-]*$');
alter domain filename_schema_array
	add constraint filename_schema_array_check1 check (array_to_string(VALUE, ',') ~ '^([A-Za-z0-9_.-]+(.%l)?(,|$))*$');
alter domain filename_schema_array
	add constraint filename_schema_array_check2 check ('.' != ALL(VALUE));
alter domain filename_schema_array
	add constraint filename_schema_array_check3 check ('..' != ALL(VALUE));


alter table contests alter column name type codename;
alter table tasks alter column name type codename;
alter table testcases alter column codename type codename;
alter table admins alter column username type codename;
alter table users alter column username type codename;
alter table teams alter column code type codename;

alter table executables alter column filename type filename;
alter table user_test_managers alter column filename type filename;
alter table user_test_executables alter column filename type filename;
alter table printjobs alter column filename type filename;
alter table attachments alter column filename type filename;
alter table managers alter column filename type filename;

alter table files alter column filename type filename_schema;
alter table user_test_files alter column filename type filename_schema;

alter table tasks alter column submission_format type filename_schema_array;

alter table statements alter column digest type digest;
alter table attachments alter column digest type digest;
alter table managers alter column digest type digest;
alter table testcases alter column input type digest;
alter table testcases alter column output type digest;
alter table user_tests alter column input type digest;
alter table user_test_files alter column digest type digest;
alter table user_test_managers alter column digest type digest;
alter table user_test_results alter column output type digest;
alter table user_test_executables alter column digest type digest;
alter table files alter column digest type digest;
alter table executables alter column digest type digest;
alter table printjobs alter column digest type digest;

rollback; -- change this to: commit;
