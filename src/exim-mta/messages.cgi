#!/usr/bin/perl

require 5;

use strict;
use integer;
use vars qw(%in %text %config);

use Exim::Message;
use Exim::Spool;

do '../web-lib.pl'; # Required by Webmin
init_config();      # Initiate the Webmin stuff

require './module-lib.pl';

ReadParse ();

my ($sort_by, $sort_order);

my @sort_methods =  ('uli', 'size', 'time', 'sender','status');

tie my @spool, 'Exim::Spool', exec=>$config{exim_path}, conf=>$config{exim_conf};

#redirect("index.cgi") and exit(1) if not defined @spool;

if (exists $in{sort}) {
  $sort_by = parse_CGI ($in{sort}, 8, 'a-z_', @sort_methods);
  $sort_order = parse_CGI ($in{order}, 4, '0-1');

  my $spoolref = tied @spool;
  $spoolref->SORT($sort_by);
  $spoolref->REVERSE if $sort_order;
}
else {
  undef $sort_order;
}

# Webmin headers
header($text{queue_title}, '');
print '<hr/>', "\n";
print '<table width="100%"><tr align="center">';

if (not @spool) {
  print '</tr></table>', "\n";
  print '<h3>', $text{queue_no_messages}, '</h3>', "\n"
}
else {
  spool_table ();
  print '<p align="right"><b>', $text{queue_last_update}, ':', '&nbsp;' x 2, '</b>',  scalar gmtime time, '</p>';
}

# Footer
print '<hr/>', "\n";
footer ('', $text{index_title});
1;

sub spool_table
  {
    my $order = defined $sort_order?not $sort_order:1;

    print <<HTML
<table border="1" width="100%">
<tr $::tb>
<th><a href="messages.cgi?sort=uli&order=$order">$text{queue_uli}</a></th>
<th><a href="messages.cgi?sort=uli&order=$order">$text{queue_gmt_date}</a></th>
<th><a href="messages.cgi?sort=size&order=$order">$text{queue_size}</a></th>
<th><a href="messages.cgi?sort=time&order=$order">$text{queue_time}</a></th>
<th><a href="messages.cgi?sort=sender&order=$order">$text{queue_sender}</a></th>
<th><a href="messages.cgi?sort=status&order=$order">$text{queue_frozen}</a></th>
<th>$text{queue_recipients}</th>
</tr>
HTML
;

    foreach my $msg (@spool) {
      my $uli = $msg->uli;
      my $gmt = $msg->gmt;
      my $size = join '&nbsp;', reverse values %{$msg->rounded_size()};
      my $time = join '&nbsp;', reverse values %{$msg->rounded_time()};
      my $sender = $msg->sender;
      my $is_frozen = $msg->is_frozen?$text{yes}:$text{no};
      my $recipients = join("<br/>", $msg->delivered, map {"<font color=\"blue\">$_</font>"} $msg->undelivered);

      print <<HTML
<tr $::cb><td><tt><a href="message.cgi?uli=$uli">$uli</a></tt></td><td>$gmt</td><td>$size</td><td>$time</td><td>$sender</td><td>$is_frozen</td><td>$recipients</td></tr>
HTML
;
    }
    print '</table>', "\n";
  }
