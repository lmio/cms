begin;

-- Run updates 40, 41, 43, 44. (Skip 42.)

alter table contest_attachments alter column filename type filename;
alter table contest_attachments alter column digest type digest;

alter table contests
    add column registration_allow_join boolean not null default false,
    add column registration_require_team boolean not null default false,
    add column registration_auto_credentials boolean not null default true;
alter table contests
    alter column registration_allow_join drop default,
    alter column registration_require_team drop default,
    alter column registration_auto_credentials drop default;
alter table contests
    rename column require_country to registration_require_country;
alter table contests
    rename column require_school_details to registration_require_school_details;
alter table contests
    rename column allowed_grades to registration_allowed_grades;

alter table contests
    add column min_submission_interval_grace_period interval,
    add column min_user_test_interval_grace_period interval;
alter table contests
    add constraint min_submission_interval_grace_period_check
        check (min_submission_interval_grace_period > '00:00:00'::interval),
    add constraint min_user_test_interval_grace_period_check
        check (min_user_test_interval_grace_period > '00:00:00'::interval);

alter table contests
    add column registration_start timestamp,
    add column registration_stop timestamp;
alter table contests
    add constraint contests_check5
        check (registration_start is null or registration_stop is null or registration_start <= registration_stop);

rollback; -- change this to: commit;
