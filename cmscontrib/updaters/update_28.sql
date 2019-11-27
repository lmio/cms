begin;

update users set password = 'plaintext:' || password;
update participations set password = 'plaintext:' || password where password is not null;

rollback; -- change this to: commit;
