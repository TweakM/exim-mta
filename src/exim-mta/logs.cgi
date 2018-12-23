#!/usr/bin/perl

require 5;

use strict;
use integer;

use Fcntl qw(SEEK_CUR SEEK_END SEEK_SET O_RDONLY);
use Exim;
use vars qw(%config %in %text);

do '../web-lib.pl'; # Required by Webmin
init_config();      # Initiate the Webmin stuff

require './module-lib.pl';

ReadParse();

my @logs = ( 'main', 'panic', 'reject' );

my $section = ($config{log_default} or 'main');
my $lines = (abs(int($config{log_lines})) or 20);

if (exists $in{log}) {
  $section = parse_CGI ($in{log}, 8, 'a-z', @logs) or redirect("/$::module_name"), exit(1);
}

if (exists $in{lines}) {
  my $temp_lines = parse_CGI ($in{lines}, 4, '0-9');
  if (int $temp_lines > 0) {
    $lines = int $temp_lines
  }
  else {
    redirect("/$::module_name");
    exit(1);
  }
}

my $exim = Exim->new(exec=>$config{exim_path}, conf=>$config{exim_conf});
defined $exim or redirect("index.cgi") and exit(1);

my $log_files_path = $exim->log_files_path();

header($text{log_title}, '');
print '<hr/>', "\n";

log_links($section);

my $logfile = $log_files_path;
$logfile =~ s/%s/$section/;

print '<pre>', "\n";
my $loghandle;
sysopen($loghandle, $logfile, O_RDONLY) or die "Unable to open log file: $logfile\n";
binmode($loghandle);

my $maxlen = sysseek($loghandle, 0, SEEK_END);
my $len = 80 * $lines; # Rule of the thumb: 80 bytes by lines
if ($len > $maxlen) { $len = $maxlen; }

my $tail;
my $cr = 0;

while ($cr < $lines + 1) {
	my ($buf, $pos);
	sysseek($loghandle, -$len, SEEK_CUR);
	$pos = sysseek($loghandle, 0, SEEK_CUR);
	sysread($loghandle, $buf, $len);
	sysseek($loghandle, $pos, SEEK_SET);
	$tail = $buf . $tail;
	$cr +=  $buf =~ tr/\n/\n/;
	last if $pos == 0;
}

my @lines = split(/\n/, $tail);
shift(@lines);
{
	my $start = @lines - $lines;
	$start =  0 if $start < 0;
	@lines = @lines[$start .. $#lines];
	print map { html_escape($_) . "\n" } @lines;
}

$loghandle->close;
print '</pre>', "\n";

print '<form action="logs.cgi" method="post">', "\n";
print "<input type=\"hidden\" name=\"log\" value=\"$section\"/>\n";
print &text ('log_info',
	     "<input type=\"text\" name=\"lines\" size=\"3\" value=\"$lines\">",
	     "<tt>$logfile</tt>"), "\n";

print '<button type="submit">', $text{log_refresh}, '</button><br/>', "\n";
print '</form><hr/>', "\n";
footer('', $text{index_title});
1;

sub log_links
{
  my $current_log = shift;

  print '<b>', $text{log_choose}, ':</b>&nbsp;&nbsp;', "\n";
  foreach my $log (@logs) {
    if ($log eq $current_log) {
      print "<b>$log</b>";
    }
    else {
      my $logfile = $log_files_path;
      $logfile =~ s/%s/$log/;
      if (-s "$logfile") {
	print "<a href=\"logs.cgi?log=$log\">$log</a>";
      }
      else {
	print "<span style=\"text-decoration:line-through\">$log</span>";
      }
    }
    print '&nbsp;'
  }
  print '<hr/>', "\n"
}
