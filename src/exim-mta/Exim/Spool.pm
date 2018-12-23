#!/usr/bin/perl

package Exim::Spool;

require 5.005;
use strict;
use integer;
use Carp;

use Exim;

use vars qw(@ISA);

@ISA = qw(Exim);

sub _init_
  {
    my $self = shift;
    my %params = @_;
    local $_;

    my $pipe = $self->p_exec('-bp');
    require Exim::Message;
    while (not $pipe->eof()) {
      my $buffer;
      while ((my $line = $pipe->getline()) !~ /^\s+$/) { $buffer .= $line }

      my $msg =  Exim::Message->new($buffer);
      PUSH($self, $msg) if defined $msg;
    }
    return $self;
  }

sub TIEARRAY
  {
    my $class = shift;

    my %params = @_;

    my $self = Exim->new(%params);
    return undef if not defined $self;

    $$self{queue} = [];

    bless $self, $class;

    $self->_init_(%params) if not defined $params{empty};
  }

sub CLEAR
  {
    my $self = shift;
    $$self{queue} = [];
  }

sub EXTEND {
  my $self  = shift;
  my $count = shift;
  STORESIZE ($self, $count);
}

sub FETCH
  {
    my ($self, $idx) = @_;
    return $$self{queue}[$idx];
  }

sub FETCHSIZE
  {
    my $self = shift;
    scalar @{$$self{queue}}
  }

sub STORE
  {
    my ($self, $idx, $new) = @_;
    ref($new) =~ /^Exim::Message/ || croak "$new is not an 'Exim::Message' object";
    $$self{queue}[$idx] = $new
  }

sub STORESIZE {
  my $self  = shift;
  my $count = shift;
  if ( $count < FETCHSIZE($self) ) {
    foreach ( 0 .. FETCHSIZE($self) - $count - 2 ) {
      POP($self);
    }
  }
}

sub PUSH
  {
    my $self = shift;
    local $_;

    my $idx = FETCHSIZE($self);
    while ($_ = shift) { STORE($self, $idx++, $_) }
  }

sub POP
  {
    my $self = shift;

    return pop @{$$self{queue}};
  }

sub by_uli { $$a{uli} cmp $$b{uli} }
sub by_time { $$a{time} <=> $$b{time} }
sub by_size { $$a{size} <=> $$b{size} }
sub by_sender { $$a{sender} cmp $$b{sender} }
sub by_status { $$a{status} <=> $$b{status} }

sub SORT
  {
    my $self = shift;
    my $method =shift;

    my @sorted;
    if ($method eq 'time') {
      @sorted = sort by_time @{$$self{queue}}
    }
    elsif ($method eq 'size') {
      @sorted = sort by_size @{$$self{queue}}
    }
    elsif ($method eq 'sender') {
      @sorted = sort by_sender @{$$self{queue}} }
    elsif ($method eq 'status') {
      @sorted = sort by_status @{$$self{queue}} }
    else {
      @sorted = sort by_uli @{$$self{queue}}
    }

    $$self{queue} = \@sorted;
    return @sorted;
  }

sub REVERSE
  {
    my $self = shift;

    $$self{queue} = [reverse @{$$self{queue}}];
  }

1;




