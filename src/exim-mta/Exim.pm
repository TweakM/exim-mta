#!/usr/bin/perl

require 5;

package Exim;

use strict;  # Be strict !
use integer; # Be fast !
use Carp;
use File::Basename;
use File::Spec;
use FileHandle;


sub _init_exec_
  {
    my $self = shift;
    my $exec_path = shift;

    if ($exec_path) {
      substr($exec_path, 0, 1) eq '/' # Must be absolute path
      and (basename($exec_path) =~ /^exim/)
      and -x $exec_path   # Must be executable by the effective uid/gid.
      or carp "Unable to find exim binary"
      and return undef;
    }
    else { $exec_path = 'exim' }
    $$self{exec} = $exec_path;
    version($self)
  }


sub _init_conf_
  {
    my $self = shift;
    my $config_file = shift;

    if ($config_file) {
      -r $config_file or carp("Unable to read config file: $config_file"), return undef;
      $$self{conf} = $config_file;
      return $config_file;
    }
    return default_config_file($self)
  }


# Exim->new(exec => '/usr/sbin/exim', conf => '/etc/exim.conf')
# or
# Exim->new() which try to determine default values
sub new
  {
    my $class = shift;
    $class = ref($class) || $class;
    my %params = @_;

    my $self = {};

    _init_exec_ ($self, $params{'exec'}) or return undef;
    _init_conf_ ($self, $params{'conf'}) or return undef;

    bless $self, $class;
  }

# $exim->dump_command(-Mad, '1ADa-000600-1', 'test@foo.bar')
sub dump_command {
    my $self = shift;

    my $command = $self->{'exec'};
    $command .= ' -C ' . $self->{conf} if defined $self->{conf};
    $command .= ' ';
    $command .= join ' ', @_;

    return $command;
}


# $exim->b_exec(-bP => 'configure_file' )
sub b_exec
  {
    my $self = shift;
    @_ or carp '$self->error(no_clo)', return undef;

    my $sleep_count = 0;
    my $pid;

    do {
        $pid = open(EXIM, '-|');
        unless (defined $pid) {
            warn "cannot fork: $!";
            die "bailing out" if $sleep_count++ > 6;
            sleep 10;
        }
    } until defined $pid;

    if ($pid) {  # parent
	my @lines = <EXIM>;
	chomp @lines;
	if (not close (EXIM)) {
		if ($! == 0) {
			$self->{error} = $!;
		}
		else {
			croak "$self->error(child) $?";
		}
	}
	return join "\n", @lines;
    } else {  # child
	close STDERR;
	close STDIN;
 
        exec $self->{'exec'}, @_;
	exit;
    }
    # never reached
  }


# $exim->p_exec(-bP => 'configure_file' )
sub p_exec
  {
    my $self = shift;
    @_ or carp '$self->error(no_clo)', return undef;

    if (my $p = FileHandle->new('-|')) {
	return $p;
    } else {
	close STDIN;
	close STDERR; 

        exec $self->{'exec'}, @_;
	die;
    }
  }


sub option
  {
    (@_ == 2) or return undef;
    my ($self, $option) = @_;

    my $result = $$self{result};
    my $buffer = $self->b_exec(-bP => $option);
    chomp $buffer;

    if ($buffer eq $option) {
      return 1;
    }
    elsif ($buffer eq "no_$option") {
      return 0;
    }
    elsif ($buffer =~ /=/) {
	$buffer =~ /=\s(.*)$/;
	return $1;
    }
    else {
      return undef;
    }
  }

# Return the current version of exim
# version()
sub version
  {
    my $self = shift;

    if (not defined $$self{_version}) {
      my $output = b_exec($self, '-bV') or return undef;

      ($$self{_version}) = ($output =~ /^Exim version (\d+\.\d+)/);
    }
    return $$self{_version};
  }

# Return the default configuration file.
# $exim->default_config_file()
sub default_config_file
  {
    my $self = shift;
    my $config_file;
    
    $config_file = b_exec ($self, -bP => 'configure_file' );

    return $config_file;
  }

# Returns the path to the exim log files
# where '%s' must be replaced by 'main', 'panic' or 'reject'
# $exim->log_files_path()
sub log_files_path
  {
    my $self = shift;
    $$self{output} = 'all';
    my $line = option ($self, 'log_file_path');
    
    my @items = split /:/, $line;
    if (@items > 2) {
    	return shift @items;
    }
    elsif (@items == 2) {
    	my @path = grep (!/^syslog$/, @items);
    	return shift @path; 
    }
    elsif (@items == 1) {
      if ($items[0] eq 'syslog') {
        croak('Logging to syslog is not supported by this module')
      }
      return $items[0]
    }
    else {
	# If this value is unset, log files are written
	# in a sub-directory of the spool directory called log.
	my ($spool_dir) = $self->option('spool_directory');
	return File::Spec->catfile($self->get_spool_directory (), 'log', '%slog');
    }
  }

sub get_spool_directory
{
    my $self = shift;

    if (not defined $$self{_spool_directory}) {
	$$self{_spool_directory} = $self->option ('spool_directory');
    }

    return $$self{_spool_directory};
}

sub is_running
{
    my $self = shift;
    # XXX: give a look in /proc
    return defined $self->get_pid ();
}

sub get_pid {
    my $self = shift;
    if (not exists $self->{_pid}) {
	
	my $pid_file = $self->option ('pid_file_path');
	unless ($pid_file) {
	    $pid_file = File::Spec->catfile($self->get_spool_directory (), 'exim-daemon.pid');
	}

	if (open PID, $pid_file) {
	    $$self{_pid} = <PID>;
	    chomp $$self{_pid};
	    close PID;
	}
	else {
	    $$self{_pid} = undef;
	}
    }
    return $$self{_pid};
}

sub queue_run
  {
    my $self = shift;
    my $type = shift; # q, R, S
    my $flags = shift;

    b_exec($self, "-$type$flags", @_);
  }

1;
