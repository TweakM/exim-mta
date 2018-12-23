#!/usr/bin/perl

require 5;

use strict;
use integer;

use Exim;

use vars qw(%config %text %module_info $module_name);

do '../web-lib.pl'; # Required by Webmin
init_config();      # Initiate the Webmin stuff

require './module-lib.pl';

my $exim = Exim->new(exec=>$config{exim_path}, conf=>$config{exim_conf});

if (not defined $exim) {
  display_error_page('index_msgerror', $module_name);
  exit(1);
}

header ($text{index_title}, '', undef, 1, 1, undef,
	"Module version: $module_info{version}<br/>
<a href=\"$text{homepage}\">$text{homepage}</a>");
print '<hr/>', "\n";

print '<h2>', $text{index_monitor}, '</h2>', "\n";

my @links = ('logs.cgi', 'messages.cgi', 'stats.cgi');

my @titles = ($text{log_title}, $text{queue_title}, $text{stat_title});

my @icons = ('images/log.gif', 'images/spool.png', 'images/stat.png');

icons_table(\@links, \@titles, \@icons);

print '<p align="right">Exim version ', $exim->version(), '</p>', "\n";
print '<br/>', "\n";
print '<hr/>', "\n";
footer('/', $text{index});
1;
