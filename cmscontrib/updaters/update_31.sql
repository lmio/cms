begin;

alter table tasks
    add submission_format varchar[];

update tasks
    set submission_format = (select array_agg(filename) from submission_format_elements where task_id = tasks.id);

alter table tasks
    alter submission_format set not null;

drop table submission_format_elements;

rollback; -- change this to: commit;
