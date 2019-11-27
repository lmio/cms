begin;

create type feedback_level as enum (
    'full',
    'restricted'
);

alter table tasks
    add feedback_level feedback_level not null default 'full';
alter table tasks
    alter feedback_level drop default;

rollback; -- change this to: commit;
