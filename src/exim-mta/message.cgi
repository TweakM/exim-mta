#!/usr/bin/perl

require 5;

use strict;
use integer;
use vars qw(%in %config %text); # Some vars exported by webmin
use Exim::Message::Action;

do '../web-lib.pl'; # Required by Webmin
init_config();      # Initiate the Webmin stuff

require './module-lib.pl';

ReadParse();

# Check the CGI 'uli' syntax and eventually perform a redirection.
my $uli = parse_CGI($in{uli}, 16, 'A-Za-z0-9\-');

my $msg = Exim::Message::Action->new(uli => $uli, exec => $config{exim_path}, conf => $config{exim_conf});

defined $msg or redirect("messages.cgi") and exit();

# Webmin header
header($msg->uli, '');
print '<hr>', "\n";

my @log_lines = $msg->view_log();

map { html_escape($_) } @log_lines;

print '<table border="1" width="100%">', "\n";
print "<tr $::tb><th>$text{msg_log}</th></tr>\n";
print "<tr $::cb><td><pre>\n", @log_lines, '</pre></td></tr>';
print '</table>', "\n";

# some dynamic HTML included below...

my $mark_delivered;

if ($msg->undelivered > 1) {
    my $options = join "\n", map { "<option>$_</option>" } $msg->undelivered;
    $mark_delivered = qw(<select name="delivered" multiple="multiple">$options</select><br/><input type="submit" name="mark_delivered" value="$text{msg_mark_delivered}"/>);
}

my $sender = html_escape($msg->sender);
my $freeze_or_thaw = $msg->is_frozen?'thaw':'freeze';

print <<HTML
<form action="message_action.cgi" method="get">
<input type="hidden" name="uli" value="$uli">
<br/>
<h3>$text{msg_view}</h3>
<input type="submit" name="view_headers" value="$text{msg_view_headers}"/>
<input type="submit" name="view_body" value="$text{msg_view_body}"/>
<h3>$text{msg_manage}</h3>
<input type="submit" name="give_up" value="$text{msg_give_up}"/>
<input type="submit" name="$freeze_or_thaw" value="$text{"msg_$freeze_or_thaw"}"/>
<input type="submit" name="deliver" value="$text{msg_deliver}"/>
<input type="submit" name="remove" value="$text{msg_remove}"/>
<h3>$text{msg_modify}</h3>
<table cellpadding="10">
<tr align="center">
<td><input type="text" name="recipient"/><br/><input type="submit" name="add_recipients" value="$text{msg_add_recipients}"/></td>
<td><input type="text" name="sender" value="$sender"/><br/><input type="submit" name="edit_sender" value="$text{msg_edit_sender}"/></td>
<td>$mark_delivered</td>
<td><input type="submit" name="mark_all_delivered" value="$text{msg_mark_all_delivered}"/></td>
</tr></table>
HTML
;

print '<hr/>', "\n";
footer("messages.cgi", $text{queue_title});
1;
