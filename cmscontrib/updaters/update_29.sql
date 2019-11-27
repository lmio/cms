begin;

create type compilation_outcome as enum (
    'ok',
    'fail'
);

create type evaluation_outcome as enum (
    'ok'
);

create function fix_text(text varchar) returns varchar[] language sql immutable as
    'select case
        when text is null or jsonb_array_length(text::jsonb) = 0 then array[]::varchar[]
        when jsonb_array_length(text::jsonb) = 1 then array[replace(text::jsonb->>0, ''%d'', ''%s'')]::varchar[]
        else array[replace(text::jsonb->>0, ''%d'', ''%s''), text::jsonb->1]::varchar[] end';

alter table datasets
    alter task_type_parameters type jsonb using task_type_parameters::jsonb,
    alter score_type_parameters type jsonb using score_type_parameters::jsonb;

alter table submission_results
    alter score_details type jsonb using score_details::jsonb,
    alter public_score_details type jsonb using public_score_details::jsonb,
    add ranking_score_details_temp varchar[],
    alter compilation_text type varchar[] using fix_text(compilation_text),
    alter compilation_text set not null,
    alter compilation_outcome type compilation_outcome using compilation_outcome::compilation_outcome,
    alter evaluation_outcome type evaluation_outcome using evaluation_outcome::evaluation_outcome;
update submission_results
    set ranking_score_details_temp = array(select jsonb_array_elements_text(ranking_score_details::jsonb));
alter table submission_results
    alter ranking_score_details type varchar[] using ranking_score_details_temp,
    drop ranking_score_details_temp;

alter table evaluations
    alter text type varchar[] using fix_text(text),
    alter text set not null;

alter table user_test_results
    alter compilation_text type varchar[] using fix_text(compilation_text),
    alter compilation_text set not null,
    alter evaluation_text type varchar[] using fix_text(evaluation_text),
    alter evaluation_text set not null;

alter table users
    add preferred_languages_temp varchar[];
update users
    set preferred_languages_temp = array(select jsonb_array_elements_text(preferred_languages::jsonb));
alter table users
    alter preferred_languages type varchar[] using preferred_languages_temp,
    drop preferred_languages_temp;

alter table tasks
    add primary_statements_temp varchar[];
update tasks
    set primary_statements_temp = array(select jsonb_array_elements_text(primary_statements::jsonb));
alter table tasks
    alter primary_statements type varchar[] using primary_statements_temp,
    drop primary_statements_temp;

alter table contests
    alter allowed_localizations type varchar[] using string_to_array(allowed_localizations, ','),
    alter languages type varchar[] using string_to_array(languages, ',');

drop function fix_text;

rollback; -- change this to: commit;
