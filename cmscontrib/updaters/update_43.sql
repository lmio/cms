begin;

update contests
    set languages = case
        when languages @> array['Java / JDK']::varchar[]
            then array_remove(languages, 'Java 1.4 / gcj')
        else array_replace(languages, 'Java 1.4 / gcj', 'Java / JDK')
    end
where languages @> array['Java 1.4 / gcj']::varchar[];

delete from executables where submission_id in (select id from submissions where language = 'Java 1.4 / gcj');
update submissions set language = 'Java / JDK' where language = 'Java 1.4 / gcj';

delete from user_test_executables where user_test_id in (select id from user_tests where language = 'Java 1.4 / gcj');
update user_tests set language = 'Java / JDK' where language = 'Java 1.4 / gcj';

rollback; -- change this to: commit;
