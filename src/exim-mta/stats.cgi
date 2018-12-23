#!/usr/bin/perl
# Much of the code here is directly borrowed from 'eximstat'
# which is part of the exim tarball
# Copyright (c) 2002 University of Cambridge.
# See the file NOTICE for conditions of use and distribution.

use integer;
use strict;
use Time::Local;
use Exim;


##################################################
#             Static data                        #
##################################################
# Will convert from 'use vars' to 'our' when perl 5.6.0 is out for
# Solaris 2.6 on sunfreeware.com.
use vars qw(@tab62 @days_per_month $gig);
use vars qw($VERSION);

use vars qw(%config %text %in);

@tab62 =
  (0,1,2,3,4,5,6,7,8,9,0,0,0,0,0,0,     # 0-9
   0,10,11,12,13,14,15,16,17,18,19,20,  # A-K
  21,22,23,24,25,26,27,28,29,30,31,32,  # L-W
  33,34,35, 0, 0, 0, 0, 0,              # X-Z
   0,36,37,38,39,40,41,42,43,44,45,46,  # a-k
  47,48,49,50,51,52,53,54,55,56,57,58,  # l-w
  59,60,61);                            # x-z

@days_per_month = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334);
$gig     = 1024 * 1024 * 1024;
$VERSION = '1.16';

# Declare global variables.
use vars qw($total_received_data  $total_received_data_gigs  $total_received_count);
use vars qw($total_delivered_data $total_delivered_data_gigs $total_delivered_count);
use vars qw(%arrival_time %size %from_host %from_address);
use vars qw(%timestamp2time);			#Hash of timestamp => time.
use vars qw($last_timestamp $last_time);	#The last time convertion done.
use vars qw($i);				#General loop counter.
use vars qw($debug);				#Debug mode?

# The following are parameters whose values are
# set by command line switches:
use vars qw(%do_sender);
use vars qw($include_remote_users);
use vars qw($hist_interval $hist_number);
use vars qw($relay_pattern @queue_times);
use vars qw($cache_id_times);

# The following are modified in the parse() routine, and
# referred to in the print_*() routines.
use vars qw($queue_more_than $delayed_count $relayed_unshown $begin $end);
use vars qw(%received_count       %received_data       %received_data_gigs);
use vars qw(%delivered_count      %delivered_data      %delivered_data_gigs);
use vars qw(%received_count_user  %received_data_user  %received_data_gigs_user);
use vars qw(%delivered_count_user %delivered_data_user %delivered_data_gigs_user);
use vars qw(%transported_count    %transported_data    %transported_data_gigs);
use vars qw(%remote_delivered %relayed %delayed %had_error %errors_count);
use vars qw(@queue_bin @remote_queue_bin @received_interval_count @delivered_interval_count);

my $cache_file = "/tmp/.webmin/exim_stat_cache";

##################################################
#                   Subroutines                  #
##################################################

sub volume_rounded {
  my($x,$g) = @_;
  my($rounded);

  while ($x > $gig) {
    $g++;
    $x -= $gig;
  }

  # Values < 1 GB
  if ($g <= 0) {
    if ($x < 10000) {
      $rounded = sprintf("%6d", $x);
    }
    elsif ($x < 10000000) {
      $rounded = sprintf("%4dKB", ($x + 512)/1024);
    }
    else {
      $rounded = sprintf("%4dMB", ($x + 512*1024)/(1024*1024));
    }
  }

  # Values between 1GB and 10GB are printed in MB
  elsif ($g < 10) {
    $rounded = sprintf("%4dMB", ($g * 1024) + ($x + 512*1024)/(1024*1024));
  }

  # Handle values over 10GB
  else {
    $rounded = sprintf("%4dGB", $g + ($x + $gig/2)/$gig);
  }

  return $rounded;
}

sub add_volume {
  my($bytes_ref,$gigs_ref,$size) = @_;
  $$bytes_ref = 0 if ! defined $$bytes_ref;
  $$gigs_ref = 0 if ! defined $$gigs_ref;
  $$bytes_ref += $size;
  while ($$bytes_ref > $gig)
    {
      $$gigs_ref++;
      $$bytes_ref -= $gig;
    }
}

sub format_time {
  my($t) = pop @_;
  my($s) = $t % 60;
  $t /= 60;
  my($m) = $t % 60;
  $t /= 60;
  my($h) = $t % 24;
  $t /= 24;
  my($d) = $t % 7;
  my($w) = $t/7;
  my($p) = "";
  $p .= "$w"."w" if $w > 0;
  $p .= "$d"."d" if $d > 0;
  $p .= "$h"."h" if $h > 0;
  $p .= "$m"."m" if $m > 0;
  $p .= "$s"."s" if $s > 0 || $p eq "";
  $p;
}

sub seconds {
  my($timestamp) = @_;

  # Is the timestamp the same as the last one?
  return $last_time if ($last_timestamp eq $timestamp);

  # No. Have we got the timestamp cached?
  if ($cache_id_times && $timestamp2time{$timestamp}) {
    return($timestamp2time{$timestamp});
  }

  return 0 unless ($timestamp =~ /^(\d{4})\-(\d\d)-(\d\d)\s(\d\d):(\d\d):(\d\d)/);
  my(@timestamp) = ($1,$2,$3,$4,$5,$6);


  #Adjust the values, as per gmtime(), and then reverse it to
  #to put it into the correct order.
  $timestamp[0] -= 1900;
  $timestamp[1]--;
  my $time = timegm(reverse @timestamp);
  if ($cache_id_times) {
    $timestamp2time{$timestamp} = $time;
  }

  # Store the last timestamp received.
  $last_timestamp = $timestamp;
  $last_time      = $time;

  $time;
}

sub id_seconds {
  my($sub_id) = substr((pop @_), 0, 6);
  my($s) = 0;
  my(@c) = split(//, $sub_id);
  while($#c >= 0) { $s = $s * 62 + $tab62[ord(shift @c) - ord('0')] }
  $s;
}

sub print_queue_times {
  no integer;
  my($string,$array,$queue_more_than) = @_;

  my $printed_one = 0;
  my $cumulative_percent = 0;

  my $queue_total = $queue_more_than;
  for ($i = 0; $i <= $#queue_times; $i++) { $queue_total += $$array[$i] }

  my($format);
  print '<hr/>', "\n";
  print "<a name=\"${string}_time\"></a>", '<h3>', text('stat_time_spent_on_queue', $text{"stat_$string"}), '</h3>', "\n";
  print '<table border="1">', "\n";
  print "<tr $::tb><th>\u$text{time}</th><th>\u$text{messages}</th><th>$text{stat_percentage}</th><th>$text{stat_cumulative_percentage}</th>\n";
  $format = "<tr $::cb><td>%s %s</td><td>%d</td><td>%5.1f%%</td><td>%5.1f%%</td>\n";

  for ($i = 0; $i <= $#queue_times; $i++)
    {
      if ($$array[$i] > 0)
	{
	  my $percent = ($$array[$i] * 100)/$queue_total;
	  $cumulative_percent += $percent;
	  printf($format,
		 $printed_one? "     " : "Under",
		 format_time($queue_times[$i]),
		 $$array[$i], $percent, $cumulative_percent);
	  $printed_one = 1;
	}
    }

  if ($queue_more_than > 0)
    {
      my $percent = ($queue_more_than * 100)/$queue_total;
      $cumulative_percent += $percent;
      printf($format,
	     "Over ",
	     format_time($queue_times[$#queue_times]),
	     $queue_more_than, $percent, $cumulative_percent);
    }

  print '</table>', "\n";
}

sub print_histogram {
  my($text) = shift;
  my(@interval_count) = @_;
  my($maxd) = 0;
  for ($i = 0; $i < $hist_number; $i++)
    { $maxd = $interval_count[$i] if $interval_count[$i] > $maxd; }

  my $scale = int(($maxd + 25)/50);
  $scale = 1 if $scale == 0;

  my($type);
  if ($text eq "deliveries")
    {
      $type = ($scale == 1)? $text{delivery} : $text{deliveries};
    }
  else
    {
      $type = ($scale == 1)? $text{message} : $text{messages};
    }

  my($temp) = text("stat_${text}_per_time",
		      ($hist_interval == 60)? $text{hour} :
		      ($hist_interval == 1)?  $text{minute} : "$hist_interval $text{minutes}", $scale, $type);

  print '<hr/>', "\n";
  print "<a name=\"$text\">", '</a>', '<h3>', $temp, '</h3>', "\n";
  print '<pre>', "\n";

  my $hour = 0;
  my $minutes = 0;
  for ($i = 0; $i < $hist_number; $i++)
    {
      my $c = $interval_count[$i];

      # If the interval is an hour (the maximum) print the starting and
      # ending hours as a label. Otherwise print the starting hour and
      # minutes, which take up the same space.

      if ($config{stat_hist_opt} == 1)
	{
	  printf("%02d-%02d", $hour, $hour + 1);
	  $hour++;
	}
      else
	{
	  if ($minutes == 0)
	    { printf("%02d:%02d", $hour, $minutes) }
	  else
	    { printf("  :%02d", $minutes) }
	  $minutes += $hist_interval;
	  if ($minutes >= 60)
	    {
	      $minutes = 0;
	      $hour++;
	    }
	}

      printf(" %6d %s\n", $c, "." x ($c/$scale));
    }
  print "\n";
  print '</pre>', "\n";
}

sub print_league_table {
  my($text,$m_count,$m_data,$m_data_gigs) = @_;

  my($format);
  print '<hr/>', "\n";
  print "<a name=\"${text}_count\"></a>", '<h3>', text('stat_top', $config{stat_topcount}, $text{"stat_$text"}, $text{stat_message_count}), '</h3>', "\n";
  print '<table border="1">', "\n";
  print "<tr $::tb>", '<th>', ucfirst $text{messages}, '</th>', '<th>', ucfirst $text{size_unit_B}, '</th>', '<th>', ucfirst $text{"stat_$text"}, '</th>', "\n";

  # Align non-local addresses to the right (so all the .com's line up).
  # Local addresses are aligned on the left as they are userids.
  my $align = ($text !~ /local/i) ? 'right' : 'left';
  $format = "<tr $::cb><td>%d</td><td>%s</td><td align=\"$align\">%s</td>\n";

  my $count = 1;
  my($key);
  foreach $key (sort
		{
		  $$m_count{$b}     <=> $$m_count{$a} ||
		    $$m_data_gigs{$b} <=> $$m_data_gigs{$a}  ||
		      $$m_data{$b}      <=> $$m_data{$a}  ||
			$a cmp $b
		      }
		keys %{$m_count})
    {
      printf($format, $$m_count{$key}, volume_rounded($$m_data{$key},$$m_data_gigs{$key}), $key);
      last if $count++ >= $config{stat_topcount};
    }
  print '</table>', "\n";
  print "\n";

  print '<hr/>', "<a name=\"${text}_volume\">", '</a>', '<h3>', text('stat_top', $config{stat_topcount}, $text{"stat_$text"}, lc $text{stat_volume}), '</h3>', "\n";
  print '<table border="1">', "\n";
  print "<tr $::tb>", '<th>', ucfirst $text{messages}, '</th>', '<th>', ucfirst $text{size_unit_B}, '</th>', '<th>', ucfirst $text{"stat_$text"}, '</th>', "\n";

  $count = 1;
  foreach $key (sort
		{
		  $$m_data_gigs{$b} <=> $$m_data_gigs{$a}  ||
		    $$m_data{$b}      <=> $$m_data{$a}  ||
		      $$m_count{$b}     <=> $$m_count{$a} ||
			$a cmp $b
		      }
		keys %{$m_count})
    {
      printf($format, $$m_count{$key}, volume_rounded($$m_data{$key},$$m_data_gigs{$key}), $key);
      last if $count++ >= $config{stat_topcount};
    }

  print "\n";
  print "</table>\n";
}

sub generate_parser {
  my $parser = '
  my($ip,$host,$email,$domain,$thissize,$size,$old,$new);
  my($tod,$m_hour,$m_min,$id,$flag);

  while ($_ = $fh->getline) {
    next if length($_) < 38;
    next unless /^(\\d{4}\\-\\d\\d-\\d\\d\\s(\\d\\d):(\\d\\d):\\d\\d)/;

    ($tod,$m_hour,$m_min) = ($1,$2,$3);
    $id   = substr($_, 20, 16);
    $flag = substr($_, 37, 2);

    #Strip away the timestamp, ID and flag (which could be "Com" for completed)
    #This speeds up the later pattern matches.
    $_ = substr($_, 40);

    $host = "local";		#Host is local unless otherwise specified.

    # Do some pattern matches to get the host and IP address.
    # We expect lines to be of the form "H=[IpAddr]" or "H=Host [IpAddr]" or
    # "H=Host (UnverifiedHost) [IpAddr]" or "H=(UnverifiedHost) [IpAddr]".
    # We do 2 separate matches to keep the matches simple and fast.
    if (/\\sH=(\\S+)/) {
      $host = $1;

    # This is Steve\'s statement. It is broken for IPv6 and it does not include
    # the square brackets in $ip.
    #  ($ip) = /\\sH=.*?\\[([\\d\\.]+)\\]/;

      # This is PH\'s statement.
      ($ip) = /\\sH=.*?(\\s\\[[^]]+\\])/;
      # If there is only an IP address, it will be in $host and $ip will be
      # unset. That is OK, because we only use $ip in conjunction with $host
      # below. But make it empty to avoid warning messages.
      $ip = "" if !defined $ip;

      #IFDEF ($do_sender{domain})
      if ($host !~ /^\\[/ && $host =~ /^(\\(?)[^\\.]+\\.([^\\.]+\\..*)/) {
	# Remove the host portion from the DNS name. We ensure that we end up with
	# at least xxx.yyy. $host can be "(x.y.z)" or  "x.y.z".
	$domain = $1.$2;
      }
      #ENDIF ($do_sender{domain})

    }

    #IFDEF ($do_sender{email})
    $email = (/^(\S+)/) ? $1 : "";
    #ENDIF ($do_sender{email})

    if ($tod lt $begin) {
      $begin = $tod;
    }
    elsif ($tod gt $end) {
      $end   = $tod;
    }


    if ($flag eq "<=") {
      $thissize = (/\\sS=(\\d+)( |$)/) ? $1 : 0;
      $size{$id} = $thissize;

      #IFDEF ($config{stat_show_relay})
      if ($host ne "local") {
	# Save incoming information in case it becomes interesting
	# later, when delivery lines are read.
	my($from) = /^(\\S+)/;
	$from_host{$id} = "$host$ip";
	$from_address{$id} = $from;
      }
      #ENDIF ($config{stat_show_relay})

      #IFDEF ($config{stat_local_league_table} || $include_remote_users)
	if (/\sU=(\\S+)/) {
	  my $user = $1;

	  #IFDEF ($config{stat_local_league_table} && $include_remote_users)
	  {				#Store both local and remote users.
	  #ENDIF ($config{stat_local_league_table} && $include_remote_users)

	  #IFDEF ($config{stat_local_league_table} && ! $include_remote_users)
	  if ($host eq "local") {		#Store local users only.
	  #ENDIF ($config{stat_local_league_table} && ! $include_remote_users)

	  #IFDEF ($include_remote_users && ! $config{stat_local_league_table})
	  if ($host ne "local") {		#Store remote users only.
	  #ENDIF ($include_remote_users && ! $config{stat_local_league_table})

	    $received_count_user{$user}++;
	    add_volume(\\$received_data_user{$user},\\$received_data_gigs_user{$user},$thissize);
          }
	}
      #ENDIF ($config{stat_local_league_table} || $include_remote_users)

      #IFDEF ($do_sender{host})
	$received_count{host}{$host}++;
	add_volume(\\$received_data{host}{$host},\\$received_data_gigs{host}{$host},$thissize);
      #ENDIF ($do_sender{host})

      #IFDEF ($do_sender{domain})
      if (defined $domain) {
	$received_count{domain}{$domain}++;
	add_volume(\\$received_data{domain}{$domain},\\$received_data_gigs{domain}{$domain},$thissize);
      }
      #ENDIF ($do_sender{domain})

      #IFDEF ($do_sender{email})
      if (defined $email) {
	$received_count{email}{$email}++;
	add_volume(\\$received_data{email}{$email},\\$received_data_gigs{email}{$email},$thissize);
      }
      #ENDIF ($do_sender{email})

      $total_received_count++;
      add_volume(\\$total_received_data,\\$total_received_data_gigs,$thissize);

      #IFDEF ($#queue_times >= 0)
	$arrival_time{$id} = $tod;
      #ENDIF ($#queue_times >= 0)

      #IFDEF ($config{stat_hist_opt} > 0)
	$received_interval_count[($m_hour*60 + $m_min)/$hist_interval]++;
      #ENDIF ($config{stat_hist_opt} > 0)
    }
    elsif ($flag eq "=>") {
      $size = $size{$id} || 0;
      if ($host ne "local") {
        $remote_delivered{$id} = 0 if !defined($remote_delivered{$id});
        $remote_delivered{$id}++;


        #IFDEF ($config{stat_show_relay})
        # Determine relaying address if either only one address listed,
        # or two the same. If they are different, it implies a forwarding
        # or aliasing, which is not relaying. Note that for multi-aliased
        # addresses, there may be a further address between the first
        # and last.

        if (defined $from_host{$id}) {
          if (/^(\\S+)(?:\\s+\\([^)]\\))?\\s+<([^>]+)>/) {
            ($old,$new) = ($1,$2);
	  }
          else {
	    $old = $new = "";
	  }

          if ("\\L$new" eq "\\L$old") {
            ($old) = /^(\\S+)/ if $old eq "";
            my $key = "H=\\L$from_host{$id}\\E A=\\L$from_address{$id}\\E => " .
              "H=\\L$host\\E$ip A=\\L$old\\E";
            if (!defined $relay_pattern || $key !~ /$relay_pattern/o) {
              $relayed{$key} = 0 if !defined $relayed{$key};
              $relayed{$key}++;
	    }
            else {
	      $relayed_unshown++
            }
          }
        }
        #ENDIF ($config{stat_show_relay})

      }

      #IFDEF ($config{stat_local_league_table} || $include_remote_users)
	#IFDEF ($config{stat_local_league_table} && $include_remote_users)
	{				#Store both local and remote users.
	#ENDIF ($config{stat_local_league_table} && $include_remote_users)

	#IFDEF ($config{stat_local_league_table} && ! $include_remote_users)
	if ($host eq "local") {		#Store local users only.
	#ENDIF ($config{stat_local_league_table} && ! $include_remote_users)

	#IFDEF ($include_remote_users && ! $config{stat_local_league_table})
	if ($host ne "local") {		#Store remote users only.
	#ENDIF ($include_remote_users && ! $config{stat_local_league_table})

	  if (my($user) = split((/</)? " <" : " ", $_)) {
	    if ($user =~ /^[\\/|]/) {
	      my($parent) = $_ =~ /(<[^@]+@?[^>]*>)/;
	      $user = "$user $parent" if defined $parent;
	    }
	    $delivered_count_user{$user}++;
	    add_volume(\\$delivered_data_user{$user},\\$delivered_data_gigs_user{$user},$size);
	  }
	}
      #ENDIF ($config{stat_local_league_table} || $include_remote_users)

      #IFDEF ($do_sender{host})
	$delivered_count{host}{$host}++;
	add_volume(\\$delivered_data{host}{$host},\\$delivered_data_gigs{host}{$host},$size);
      #ENDIF ($do_sender{host})
      #IFDEF ($do_sender{domain})
      if (defined $domain) {
	$delivered_count{domain}{$domain}++;
	add_volume(\\$delivered_data{domain}{$domain},\\$delivered_data_gigs{domain}{$domain},$size);
      }
      #ENDIF ($do_sender{domain})
      #IFDEF ($do_sender{email})
      if (defined $email) {
	$delivered_count{email}{$email}++;
	add_volume(\\$delivered_data{email}{$email},\\$delivered_data_gigs{email}{$email},$size);
      }
      #ENDIF ($do_sender{email})

      $total_delivered_count++;
      add_volume(\\$total_delivered_data,\\$total_delivered_data_gigs,$size);

      #IFDEF ($config{stat_show_transport})
        my $transport = (/\\sT=(\\S+)/) ? $1 : ":blackhole:";
        $transported_count{$transport}++;
        add_volume(\\$transported_data{$transport},\\$transported_data_gigs{$transport},$size);
      #ENDIF ($config{stat_show_transport})

      #IFDEF ($config{stat_hist_opt} > 0)
        $delivered_interval_count[($m_hour*60 + $m_min)/$hist_interval]++;
      #ENDIF ($config{stat_hist_opt} > 0)
    }
    elsif ($flag eq "==" && defined($size{$id}) && !defined($delayed{$id})) {
      $delayed_count++;
      $delayed{$id} = 1;
    }
    elsif ($flag eq "**") {
      $had_error{$id} = 1 if defined ($size{$id});

      #IFDEF ($config{stat_show_errors})
        $errors_count{$_}++;
      #ENDIF ($config{stat_show_errors})
    }
    elsif ($flag eq "Co") {
      #Completed?
      #IFDEF ($#queue_times >= 0)
        #Note: id_seconds() benchmarks as 42% slower than seconds() and computing
        #the time accounts for a significant portion of the run time.
        my($queued);
        if (defined $arrival_time{$id}) {
          $queued = seconds($tod) - seconds($arrival_time{$id});
	  delete($arrival_time{$id});
        }
        else {
	  $queued = seconds($tod) - id_seconds($id);
        }

        for ($i = 0; $i <= $#queue_times; $i++) {
          if ($queued < $queue_times[$i]) {
            $queue_bin[$i]++;
            $remote_queue_bin[$i]++ if $remote_delivered{$id};
            last;
	  }
	}
        $queue_more_than++ if $i > $#queue_times;
      #ENDIF ($#queue_times >= 0)

      # Get rid of data no longer needed - saves memory

      #IFDEF ($config{stat_show_relay})
        delete($from_host{$id});
        delete($from_address{$id});
      #ENDIF ($config{stat_show_relay})

      delete($size{$id});
    }
  }';

  # We now do a 'C preprocessor style operation on our parser
  # to remove bits not in use.
  my(%defines_in_operation,$removing_lines,$processed_parser);
  foreach (split (/\n/,$parser)) {
    if ((/^\s*#\s*IFDEF\s*\((.*?)\)/i  && ! eval $1) ||
	(/^\s*#\s*IFNDEF\s*\((.*?)\)/i &&   eval $1)	) {
      $defines_in_operation{$1} = 1;
      $removing_lines = 1;
    }

    $processed_parser .= $_."\n" unless $removing_lines;

    if (/^\s*#\s*ENDIF\s*\((.*?)\)/i) {
      delete $defines_in_operation{$1};
      unless (keys %defines_in_operation) {
	$removing_lines = 0;
      }
    }
  }
  print "# START OF PARSER:\n$processed_parser\n\n# END OF PARSER\n" if $debug;

  return $processed_parser;
}

sub parse {
  my($parser,$fh) = @_;

  eval $parser;
  die ($@) if $@;
}

sub print_header {
  print "<b>$text{stat_begin}</b> ", $begin, '&nbsp;';
  print "<b>$text{stat_end}</b> ", $end, '.<br/>';

  print '<ul>', "\n";
  print '<li>', '<a href="#grandtotal">', $text{stat_summary}, '</a>', '</li>', "\n";
  print '<li>', '<a href="#transport">', $text{stat_deliveries_by_transport}, '</a>', '</li>', "\n" if $config{stat_show_transport};
  if ($config{stat_hist_opt}) {
    print '<li>', '<a href="#received">', $text{stat_received_header}, '</a>', '</li>', "\n";
    print '<li>', '<a href="#deliveries">', $text{stat_deliveries_header}, '</a>', '</li>', "\n";
  }
  if ($#queue_times >= 0) {
    print '<li>', '<a href="#all_messages_time">', text("stat_time_spent_on_queue", $text{stat_all_messages}), '</a>', '</li>', "\n";
    print '<li>', '<a href="#messages_with_at_least_one_remote_delivery_time">', text("stat_time_spent_on_queue", $text{stat_messages_with_at_least_one_remote_delivery}), '</a>', '</li>', "\n";
  }
  print '<li>', '<a href="#relayed">', $text{stat_relayed}, '</a>', '</li>', "\n" if $config{stat_show_relay};
  if ($config{stat_topcount}) {
    foreach ('host','domain','email') {
      next unless $do_sender{$_};
      print '<li>', "<a href=\"#sending_${_}_count\">", text('stat_top', $config{stat_topcount}, $text{"stat_sending_$_"}, $text{stat_message_count}), '</a>', '</li>', "\n";
      print '<li>', "<a href=\"#sending_${_}_volume\">", text('stat_top', $config{stat_topcount}, $text{"stat_sending_${_}"}, $text{stat_volume}), '</a>', '</li>', "\n";
    }
    if ($config{stat_local_league_table}) {
      print '<li><a href="#local_senders_count">', text('stat_top', $config{stat_topcount}, $text{stat_local_senders}, $text{stat_message_count}), '</a>', '</li>', "\n";
      print '<li><a href="#local_senders_volume">', text('stat_top', $config{stat_topcount}, $text{stat_local_senders}, $text{stat_volume}), '</a>', '</li>', "\n";
    }
    foreach ('host','domain','email') {
      next unless  $do_sender{$_};
      print '<li>', "<a href=\"#${_}_destination_count\">", text('stat_top', $config{stat_topcount}, $text{"stat_${_}_destination"}, $text{stat_message_count}), '</a>', '</li>',"\n";
      print '<li>', "<a href=\"#${_}_destination_volume\">", text('stat_top', $config{stat_topcount}, $text{"stat_${_}_destination"}, $text{stat_volume}), '</a>', '</li>', "\n";
    }
    if ($config{stat_local_league_table}) {
      print "<li><a href=\"#local_destination_count\">Top $config{stat_topcount} local destinations by message count</a></li>\n";
      print "<li><a href=\"#local_destination_volume\">Top $config{stat_topcount} local destinations by volume</a></li>\n";
    }
  }
  print "<li><a href=\"#errors\">$text{stat_list_of_errors}</a></li>\n" if $config{stat_show_errors};
  print "</ul>\n<hr/>\n";
}

sub print_grandtotals {
  # Get the sender by headings and results. This is complicated as we can have
  # different numbers of columns.
  my($sender_html_header, $sender_html_format);
  my(@received_totals,@delivered_totals);
  foreach ('host','domain','email') {
    if ($do_sender{$_}) {
      push(@received_totals,scalar(keys %{$received_data{$_}}));
      push(@delivered_totals,scalar(keys %{$delivered_data{$_}}));
      $sender_html_header .= "<th>\u$text{\"stat_$_\"}</th>";
      $sender_html_format .= "<td>%d</td>";
    }
  }

  my($format1,$format2);
print << "EoText";
<a name="grandtotal"></a>
<h3>$text{stat_summary}</h3>
<table border="1">
<tr $::tb><th>TOTAL</th><th>\u$text{stat_volume}</th><th>\u$text{messages}</th>$sender_html_header<th colspan="2">$text{stat_delayed}</th><th colspan="2">$text{stat_failed}</th></tr>
EoText

  $format1 = "<tr $::cb><td $::tb>%s</td><td>%s</td>$sender_html_format<td>%d</td>";
  $format2 = "<td>%d</td><td>%4.1f%%</td><td>%d</td><td>%4.1f%%</td></tr>";

  my $volume = volume_rounded($total_received_data, $total_received_data_gigs);
  my $failed_count = keys %had_error;
    {
    no integer;
    printf("$format1$format2\n",$text{stat_received},$volume,$total_received_count,
      @received_totals,$delayed_count,
      ($total_received_count) ? ($delayed_count*100/$total_received_count) : 0,
      $failed_count,
      ($total_received_count) ? ($failed_count*100/$total_received_count) : 0);
    }

  $volume = volume_rounded($total_delivered_data, $total_delivered_data_gigs);
  printf("$format1\n\n",$text{stat_delivered},$volume,$total_delivered_count,@delivered_totals);
  print '</table>', "\n";
}

sub print_transport {
  my($format1);
  print '<hr/>', "\n";
  print '<a name="transport"></a>', '<h3>', $text{stat_deliveries_by_transport}, '</h3>', "\n";
  print '<table border="1">', "\n";
  print "<tr $::tb><th>$text{stat_transport}</th><th>\u$text{stat_volume}</th><th>\u$text{messages}</th></tr>\n";
  $format1 = "<tr $::cb><td>%s</td><td>%s</td><td>%d</td></tr>";

  my($key);
  foreach $key (sort keys %transported_data) {
    printf("$format1\n",$key,
      volume_rounded($transported_data{$key},$transported_data_gigs{$key}),
      $transported_count{$key});
  }
  print '</table>', "\n";
  print "\n";
}

sub print_relay {
  print '<hr/>', '<a name="relayed">', '</a>', '<h3>', $text{stat_relayed}, '</h3>', "\n";
  if (scalar(keys %relayed) > 0 || $relayed_unshown > 0) {
    my $shown = 0;
    my $spacing = "";
    my($format);

    print '<table border="1">', "\n";
    print "<tr $::tb><th>Count</th><th>From</th><th>To</th></tr>\n";
    $format = "<tr $::cb><td>%d</td><td>%s</td><td>%s</td></tr>\n";

    my($key);
    foreach $key (sort keys %relayed) {
      my $count = $relayed{$key};
      $shown += $count;
      $key =~ s/[HA]=//g;
      my($one,$two) = split(/=> /, $key);
      printf($format, $count, $one, $two);
      $spacing = "\n";
    }
    print '</table>', "\n";
    print "<p>${spacing}Total: $shown (plus $relayed_unshown unshown)</p>\n";
  }
  else {
    print $text{stat_no_relayed_messages}, "\n";
  }
  print "\n";
}

sub print_errors {
  my $total_errors = 0;

  print "<hr/><a name=\"errors\"></a><h3>$text{stat_list_of_errors}</h3>\n";
  if (scalar(keys %errors_count) != 0) {
    my($format);
    print '<ul>';
    $format = "<li>(%d) &times; %s</li>\n";

    foreach my $key (sort keys %errors_count) {
      my $text = $key;
      chop($text);
      $total_errors += $errors_count{$key};
      printf($format,$errors_count{$key},$text);
    }
    print "</ul>\n<p>\n";
    if ($total_errors == 1) {
      print '<p><b>', $text{stat_one_error}, '</b></p>'
    }
    else {
      print '<p><b>', &text('stat_errors', $total_errors), '</b></p>'
    }
  }
  else {
    print '<p><b>', $text{stat_no_errors}, '</b></p>'
  }
  print "\n";
}

sub init {
  $last_timestamp = 0;

  $total_received_data = 0;
  $total_received_data_gigs = 0;
  $total_received_count = 0;

  $total_delivered_data = 0;
  $total_delivered_data_gigs = 0;
  $total_delivered_count = 0;

  $queue_more_than = 0;
  $delayed_count = 0;
  $relayed_unshown = 0;
  $begin = "9999-99-99 99:99:99";
  $end = "0000-00-00 00:00:00";

  $include_remote_users = 0;

  @queue_times = (60, 5*60, 15*60, 30*60, 60*60, 3*60*60, 6*60*60,
		  12*60*60, 24*60*60);

  for (my $i = 0; $i <= $#queue_times; $i++) {
    $queue_bin[$i] = 0;
    $remote_queue_bin[$i] = 0;
  }

  # Compute the number of slots for the histogram
  if ($config{stat_hist_opt} > 0)
    {
      if ($config{stat_hist_opt} > 60 || 60 % $config{stat_hist_opt} != 0)
	{
	  print "must specify a factor of 60\n";
	  exit 1;
	}
      $hist_interval = 60/$config{stat_hist_opt};
      $hist_number = (24*60)/$hist_interval;
      @received_interval_count = (0) x $hist_number;
      @delivered_interval_count = (0) x $hist_number;
    }
  foreach my $sort (split /,/, $config{stat_do_sender}) {
    if ($sort eq 'host')   { $do_sender{host} = 1 }
    elsif ($sort eq 'domain') { $do_sender{domain} = 1 }
    elsif ($sort eq 'email')  { $do_sender{email} = 1 }
  }

  # Default to display tables by sending Host.
  $do_sender{host} = 1 unless ($do_sender{domain} || $do_sender{email});
}

##################################################
#                 Main Program                   #
##################################################


do '../web-lib.pl';
init_config();

ReadParse();

my $exim = Exim->new(exec=>$config{exim_path}, conf=>$config{exim_conf});

redirect("index.cgi") and exit(1) if (not defined $exim);

my $logfile = $exim->log_files_path();
$logfile =~ s/%s/main/;

# Webmin Header.
header($text{stat_title}, '');
print '<hr/>', "\n";

init();

# Generate our parser.
my $parser = generate_parser();

my $log = FileHandle->new($logfile, "r") or die "Unable to open $logfile";

#Now parse the filehandle, updating the global variables.
parse($parser, $log);

if ($begin eq "9999-99-99 99:99:99") {
  print "<h3>$text{stat_no_valid_lines}</h3>\n";
}
else {
  # Output our results.
  print_header();
  print_grandtotals();

  # Print totals by transport if required.
  print_transport() if $config{stat_show_transport};

  # Print the deliveries per interval as a histogram, unless configured not to.
  # First find the maximum in one interval and scale accordingly.
  if ($config{stat_hist_opt} > 0) {
    print_histogram('received', @received_interval_count);
    print_histogram('deliveries', @delivered_interval_count);
  }

  # Print times on queue if required.
  if ($#queue_times >= 0) {
    print_queue_times('all_messages', \@queue_bin, $queue_more_than);
    print_queue_times('messages_with_at_least_one_remote_delivery', \@remote_queue_bin, $queue_more_than);
  }

  # Print relay information if required.
  print_relay() if $config{stat_show_relay};

  # Print the league tables, if topcount isn't zero.
  if ($config{stat_topcount} > 0) {
    foreach ('host','domain','email') {
      next unless $do_sender{$_};
      print_league_table("sending_$_", $received_count{$_}, $received_data{$_},$received_data_gigs{$_});
    }

    print_league_table('local_senders', \%received_count_user,
		       \%received_data_user,\%received_data_gigs_user) if ($config{stat_local_league_table} || $include_remote_users);
    foreach ('host','domain','email') {
      next unless $do_sender{$_};
      print_league_table("\l${_}_destination", $delivered_count{$_}, $delivered_data{$_},$delivered_data_gigs{$_});
    }
    print_league_table('local_destination', \%delivered_count_user,
		       \%delivered_data_user,\%delivered_data_gigs_user) if ($config{stat_local_league_table} || $include_remote_users);
  }

  # Print the error statistics if required.
  print_errors() if $config{stat_show_errors};
}
# Footer
print '<hr/>', "\n";
footer ('', $text{index_title});
1;
