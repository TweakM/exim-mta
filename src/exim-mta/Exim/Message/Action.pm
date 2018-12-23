#!/usr/bin/perl

package Exim::Message::Action;

require 5;

use strict;
use integer;
use Carp;
use Exim;
use Exim::Message;
use HTML::Entities; # used to encode html from message body

use vars qw(@ISA);

@ISA = qw(Exim Exim::Message);

my %actions = (
	deliver => '-M',
	freeze => '-Mf',
	thaw => '-Mt',
	give_up => '-Mg',
	remove => '-Mrm',
	view_body => '-Mvb',
	view_log => '-Mvl',
	view_headers => '-Mvh',
	add_recipients => '-Mar',
	edit_sender => '-Mes',
	mark_delivered => '-Mmd',
	mark_all_delivered => '-Mmad'
);


sub _init_
  {
    my $self = shift;

    my $msg = Exim::Message->new( $self->b_exec(-bp => shift) );

    defined $msg or return undef;

    # Ugly....
    foreach my $key (keys %{$msg}) { $$self{$key} = $$msg{$key} }

    return $self
  }

sub new
  {
    my $class = shift;
    $class = ref($class) || $class;
    my %params = @_;

    my $self = Exim->new(%params);
    return undef if not defined $self;

    bless $self, $class;

    if (defined $params{uli}) {
      _init_($self, $params{uli}) or return undef;
    }
  }

sub deliver
  {
    my $self = shift;

    return $self->b_exec(-M => $$self{uli});
  }

sub freeze
  {
    my $self = shift;

    return $self->b_exec(-Mf => $$self{uli});
  }

sub thaw
  {
    my $self = shift;

    return $self->b_exec(-Mt => $$self{uli});
  }

sub give_up
  {
    my $self = shift;

    return $self->b_exec(-Mg => $$self{uli});
  }

sub remove
  {
    my $self = shift;

    return $self->b_exec(-Mrm => $$self{uli});
  }

sub view_body
  {
    my $self = shift;

    return encode_entities($self->b_exec(-Mvb => $$self{uli}));
  }

sub view_log
  {
    my $self = shift;

    return $self->b_exec(-Mvl => $$self{uli});
  }

sub view_headers
  {
    my $self = shift;

    return $self->b_exec(-Mvh => $$self{uli});
  }

sub add_recipients
  {
    my $self = shift;

    return $self->b_exec(-Mar => $$self{uli}, @_);
  }

sub edit_sender
  {
    my $self = shift;
    
    return $self->b_exec('-Mes', $$self{uli}, shift());
  }

sub mark_delivered
  {
    my $self = shift;

    return $self->b_exec(-Mmd => $$self{uli}, @_);
  }

sub mark_all_delivered
  {
    my $self = shift;

    return $self->b_exec(-Mmad => $$self{uli});
  }

sub dump_command
  {
	my $self = shift;
	my $action = shift;

	if (exists $actions{$action}) {
		return $self->SUPER::dump_command($actions{$action}, $self->{uli}, @_)
	}
	croak 'unknow action';
  }
