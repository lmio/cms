begin;

alter table contests
    alter allowed_grades type integer[] using string_to_array(allowed_grades, ',')::integer[];

alter table schools
    add email varchar;

alter table teacher_registrations
    alter email drop not null;

alter table users
    add registered_by varchar;

rollback; -- change this to: commit;
