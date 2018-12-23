#!/usr/bin/perl

require 5;

use strict;
use integer;
use vars qw{%in %config %text};
use Exim::Message::Action;

do '../web-lib.pl'; # Required by Webmin
init_config();      # Initiate the Webmin stuff

require './module-lib.pl';

ReadParse();

# Check the CGIs 'uli' and 'action' syntax and eventually perform a redirection.
my $uli = parse_CGI ($in{uli}, 16, 'A-Za-z0-9\-');
my $action;

my $msg = Exim::Message::Action->new(uli=>$uli, exec=>$config{exim_path}, conf=>$config{exim_conf});

defined $msg or redirect("messages.cgi"), exit(1);

my @actions = ('deliver', 'thaw', 'freeze', 'thaw', 'give_up', 'remove', 'view_log', 'view_headers', 'view_body', 'add_recipients', 'edit_sender', 'mark_delivered', 'mark_all_delivered', undef);

foreach (@actions) {
  $action = $_ and last if exists $in{$_};
}

defined $action
#  and grep /^$action$/, @actions
  or redirect("messages.cgi"), exit();

# Webmin header
header($msg->uli, '');
print '<hr/>', "\n";

print '<table border="1">', "\n";

my @addrs;
if ($action eq 'add_recipients') {
  defined $in{recipient} or redirect("messages.cgi"), exit();
  push @addrs, $in{recipient}
}
elsif ($action eq 'edit_sender') {
  defined $in{sender} or redirect("messages.cgi"), exit();
  push @addrs, $in{sender}
}
elsif ($action eq 'mark_delivered') {
  defined $in{delivered} or redirect("messages.cgi"), exit();
  push @addrs, $in{delivered}
}
elsif ($action eq 'view_body') {
}

#foreach my $addr (@addrs) {
   # !!!! vérifier les caractères autorisés dans la RFC822 (?)
#  parse_CGI($addr, 255, 'a-zA-Z0-9\-_\.\@');
#}

print "<tr $::tb><th>", $text{msg_command}, "</th></tr>\n";
print "<tr $::cb><td>", $msg->dump_command($action, @addrs), "</td></tr>\n";
print "<tr $::tb><th>", $text{msg_result}, "</th></tr>\n";

my @result = $msg->$action(@addrs);
my $first_line = shift @result;

print "<tr $::cb><td><pre>\n";
print $first_line if not $first_line =~/^$uli\-(H|D)\s*$/;
print  join "\n", map { html_escape($_) } @result;
print '</pre></td></tr>', "\n";
print '</table>', "\n";
print '<p/>';
#Footer
print '<hr/>', "\n";
footer("message.cgi?uli=".$msg->uli, $msg->uli,
	"messages.cgi", $text{queue_title});
1;
