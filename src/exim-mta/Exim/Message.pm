#!/usr/bin/perl

package Exim::Message;

require 5;

use strict;
use integer;

sub uli # 'uli' stands for Unique Local Identifier
  {
    my $self = shift;
    if (@_) {
      my $uli = shift;

      return undef if $uli !~ /[0-9a-zA-Z]{6}-[0-9a-zA-Z]{6}-[0-9a-zA-Z]{2}/;
      $self->{uli} = $uli
    }
    return $$self{uli}
  }

sub time
  {
    my $self = shift;
    if (@_) {
      my $time = shift;
      my $units = 'smhdw';

      $time =~ /^(\d+)([$units])/ or return undef;

      $$self{rtime} = { value => $1, unit => $2 };

      my ($value, $unit) = ($1, index($units, $2));
      my @coef = (1, 60, 60, 24, 7);

      while ($unit > 0) { $value *= $coef[$unit--] }
      $$self{time} = $value;
    }
    return $$self{time}
  }

sub rounded_time
  {
    my $self = shift;
    return $$self{rtime}
  }

sub size
  {
    my $self = shift;
    if (@_) {
      my $size = shift;
      $size = defined $size?$size:0;

      my $units = '_KMG';

      my $bytes;

      if ($size =~ /\./) {
	$size =~ /^(\d+\.?\d+)([$units])?/ or return undef;
	$$self{rsize} = { value => $1, unit => $2.'B' };
	$bytes = $1*1024**index($units, $2);
      }
      else {
	$size =~ /^(\d+)([$units]?)/ or return undef;
	$$self{rsize} = { value => $1, unit => $2.'B' };
	$bytes = $1 << 10*index($units, $2);
      }

      $$self{size} = $bytes;
    }

    return $$self{size}
  }

sub rounded_size
  {
    my $self =shift;
    return $$self{rsize}
  }

sub sender
  {
    my $self = shift;
    if (@_) {
      my $sender = shift;

      $sender =~ s/^\<(.*)\>$/$1/;
      $$self{sender} = $sender;
    }
    return $$self{sender}
  }

sub status
  {
    my $self = shift;
    if (@_) { $$self{status} = shift()?1:0 }
    return $$self{status}
  }

sub undelivered
  {
    my $self = shift;
    if (@_) { push @{$$self{undelivered}}, @_ }
    return @{$$self{undelivered}};
  }

sub delivered
  {
    my $self = shift;
    if (@_) { push @{$$self{delivered}}, @_ }
    return @{$$self{delivered}};
  }

sub _init_
  {
    my $self = shift;

    my @fields = split ' ', shift;
    return undef if @fields < 4;

    &time ($self, shift @fields) or return undef;
    &size ($self, shift @fields) or return undef;
    &uli ($self, shift @fields) or return undef;
    &sender ($self, shift @fields);
    &status ($self, shift @fields);

    $$self{delivered} = [];
    $$self{undelivered} = [];

    local $_;
    foreach (@_) {
      chomp;
      next if /^$/;
      s/^\s+//;
      s/^D\s+//?&delivered($self, $_):&undelivered($self, $_)
    }
    return $self
  }

sub new
  {
    my $class = shift;
    $class = ref($class) || $class;

    my $self = bless {}, $class;

    if (@_) {
      $self->_init_ (split /\n/, shift ()) or return undef;
    }
    return $self;
  }

sub gmt
  {
    my $self = shift;

    return $$self{gmt} if defined $$self{gmt};

    return $$self{gmt} = gmtime base62_to_decimal ($$self{uli})
  }

sub is_frozen
  {
    my $self = shift;
    return $$self{status};
  }

# Converts base 62 ([0-9a-zA-Z]*) ASCII strings to decimal numbers.
# Example: &base62_to_decimal('15gY5D');
sub  base62_to_decimal
  {
    my @tab62 =
      (0,1,2,3,4,5,6,7,8,9,0,0,0,0,0,0,      # 0-9
       0,10,11,12,13,14,15,16,17,18,19,20,   # A-K
       21,22,23,24,25,26,27,28,29,30,31,32,  # L-W
       33,34,35, 0, 0, 0, 0, 0,              # X-Z
       0,36,37,38,39,40,41,42,43,44,45,46,   # a-k
       47,48,49,50,51,52,53,54,55,56,57,58,  # l-w
       59,60,61);                            # x-z

    my($d) = 0;
    my($O) = ord('0');
    my(@c) = unpack('C*', shift);
    while($#c >= 0) { $d = $d * 62 + $tab62[shift(@c) - $O] }
    return $d;
  }
