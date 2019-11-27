begin;

alter table datasets
    alter memory_limit type bigint;
alter table submission_results
    alter compilation_memory type bigint;
alter table evaluations
    alter execution_memory type bigint;
alter table user_test_results
    alter compilation_memory type bigint,
    alter execution_memory type bigint;

rollback; -- change this to: commit;
