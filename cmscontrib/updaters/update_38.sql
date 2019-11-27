begin;

update datasets
    set task_type_parameters = task_type_parameters || '["stub", "fifo_io"]'::jsonb
    where task_type = 'Communication' and jsonb_array_length(task_type_parameters) = 1;

rollback; -- change this to: commit;
